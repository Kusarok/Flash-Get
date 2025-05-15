import sys
import os
import requests
import threading
import time
import queue
import concurrent.futures
from urllib.parse import urlparse
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QProgressBar, QFileDialog, QListWidget, QListWidgetItem,
                            QMessageBox, QMenu, QStyleFactory, QFrame, QSlider,
                            QToolBar, QAction, QSizePolicy, QGraphicsDropShadowEffect,
                            QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer, QSize, QPoint
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor, QMouseEvent, QCursor

# Update color scheme to a modern palette
DARK_PRIMARY = "#1A1A2E"  # Deeper blue-black
DARK_SECONDARY = "#16213E"  # Deep blue
DARK_TERTIARY = "#0F3460"  # Rich blue
ACCENT_COLOR = "#E94560"  # Vibrant red accent
TEXT_COLOR = "#F0F0F0"  # Slightly off-white
DISABLED_COLOR = "#555555"
PROGRESS_COLOR = "#4CAF50"  # Green
CARD_SHADOW = "0px 2px 6px rgba(0, 0, 0, 0.3)"

# Default settings
DEFAULT_CONNECTIONS = 8  # Number of concurrent connections
DEFAULT_CHUNK_SIZE = 1024 * 1024 * 2  # 2MB chunks
DEFAULT_TIMEOUT = 30  # 30 seconds timeout
MAX_CONNECTIONS = 16  # Maximum number of connections

# Import the module files
from database import Database
from notifier import NotificationManager
from cloud_services import create_cloud_service, detect_cloud_service
import utils
import translations

class DownloadSignals(QObject):
    progress = pyqtSignal(str, int, str, str)  # id, progress percentage, speed, downloaded/total
    status = pyqtSignal(str, str)  # id, status message
    completed = pyqtSignal(str)  # id

class ChunkDownloader(threading.Thread):
    def __init__(self, url, start_byte, end_byte, output_file, chunk_id, chunk_queue, download_tracker):
        super().__init__()
        self.url = url
        self.start_byte = start_byte
        self.end_byte = end_byte
        self.output_file = output_file
        self.chunk_id = chunk_id
        self.chunk_queue = chunk_queue
        self.download_tracker = download_tracker
        self.daemon = True
        self.is_paused = False
        self.is_cancelled = False
        
    def run(self):
        headers = {'Range': f'bytes={self.start_byte}-{self.end_byte}'}
        
        try:
            with requests.get(self.url, headers=headers, stream=True, timeout=DEFAULT_TIMEOUT) as response:
                if response.status_code not in [206, 200]:  # Partial Content or OK
                    self.chunk_queue.put((self.chunk_id, False, f"Chunk download failed with status {response.status_code}"))
                    return
                
                total_chunk_size = self.end_byte - self.start_byte + 1
                downloaded = 0
                
                with open(f"{self.output_file}.part{self.chunk_id}", 'wb') as f:
                    start_time = time.time()
                    bytes_since_last = 0
                    
                    for data in response.iter_content(chunk_size=65536):  # 64KB sub-chunks
                        if self.is_cancelled:
                            self.chunk_queue.put((self.chunk_id, False, "Cancelled"))
                            return
                        
                        while self.is_paused:
                            time.sleep(0.1)
                            if self.is_cancelled:
                                self.chunk_queue.put((self.chunk_id, False, "Cancelled"))
                                return
                        
                        if data:
                            f.write(data)
                            data_len = len(data)
                            downloaded += data_len
                            bytes_since_last += data_len
                            
                            # Update download tracker periodically
                            current_time = time.time()
                            time_diff = current_time - start_time
                            if time_diff >= 0.5:
                                speed = bytes_since_last / time_diff
                                self.download_tracker.update_chunk_progress(self.chunk_id, bytes_since_last, speed)
                                start_time = current_time
                                bytes_since_last = 0
                
                # Final update with the total downloaded for this chunk
                self.download_tracker.update_chunk_progress(self.chunk_id, 0, 0, total_chunk_size)
                self.chunk_queue.put((self.chunk_id, True, "Completed"))
                
        except Exception as e:
            self.chunk_queue.put((self.chunk_id, False, str(e)))

class DownloadTracker:
    def __init__(self, total_size, num_chunks):
        self.total_size = total_size
        self.chunks_progress = [0] * num_chunks
        self.chunks_speeds = [0] * num_chunks
        self.lock = threading.Lock()
        self.total_downloaded = 0
        self.current_speed = 0
        
    def update_chunk_progress(self, chunk_id, bytes_downloaded, speed, total_chunk_size=None):
        with self.lock:
            if total_chunk_size is not None:
                # Final update with total size
                self.chunks_progress[chunk_id] = total_chunk_size
            else:
                # Incremental update
                self.chunks_progress[chunk_id] += bytes_downloaded
                self.chunks_speeds[chunk_id] = speed
            
            self.total_downloaded = sum(self.chunks_progress)
            self.current_speed = sum(self.chunks_speeds)

class DownloadThread(threading.Thread):
    def __init__(self, url, save_path, download_id, signals, num_connections=DEFAULT_CONNECTIONS):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.download_id = download_id
        self.signals = signals
        self.num_connections = min(num_connections, MAX_CONNECTIONS)
        self.is_paused = False
        self.is_cancelled = False
        self.daemon = True  # Thread will end when main program exits
        self.chunk_downloaders = []
        
    def run(self):
        file_name = os.path.basename(urlparse(self.url).path) or 'download'
        full_path = os.path.join(self.save_path, file_name)
        temp_path = full_path + ".download"
        
        try:
            # Get file size
            self.signals.status.emit(self.download_id, "Checking file info...")
            response = requests.head(self.url, timeout=DEFAULT_TIMEOUT)
            
            # Check if server supports range requests
            supports_range = 'accept-ranges' in response.headers and response.headers['accept-ranges'] == 'bytes'
            
            # Get total file size
            total_size = int(response.headers.get('content-length', 0))
            
            if total_size == 0:
                self.signals.status.emit(self.download_id, "Error: Could not determine file size")
                return
            
            # Check if the file is already downloaded
            if os.path.exists(full_path) and os.path.getsize(full_path) == total_size:
                self.signals.status.emit(self.download_id, "File already downloaded")
                downloaded_str = f"{self.format_size(total_size)} / {self.format_size(total_size)}"
                self.signals.progress.emit(self.download_id, 100, "0 KB/s", downloaded_str)
                self.signals.completed.emit(self.download_id)
                return
                
            # If range requests aren't supported, fall back to single connection
            if not supports_range:
                self.signals.status.emit(self.download_id, "Server doesn't support multi-connection downloads, using single connection")
                self.num_connections = 1
            
            # Calculate chunk sizes
            chunk_size = total_size // self.num_connections
            if chunk_size < 1024 * 1024:  # If chunks would be smaller than 1MB
                self.num_connections = max(1, total_size // (1024 * 1024))
                chunk_size = total_size // self.num_connections
            
            self.signals.status.emit(self.download_id, f"Starting download with {self.num_connections} connections...")
            
            # Create download tracker
            download_tracker = DownloadTracker(total_size, self.num_connections)
            
            # Create a queue for chunk completion messages
            chunk_queue = queue.Queue()
            
            # Create and start chunk downloaders
            for i in range(self.num_connections):
                start_byte = i * chunk_size
                # Last chunk gets the remainder
                end_byte = total_size - 1 if i == self.num_connections - 1 else start_byte + chunk_size - 1
                
                chunk_downloader = ChunkDownloader(
                    self.url, start_byte, end_byte, temp_path, i, chunk_queue, download_tracker
                )
                self.chunk_downloaders.append(chunk_downloader)
                chunk_downloader.start()
            
            # Monitor download progress
            chunks_completed = 0
            chunks_failed = []
            start_time = time.time()
            download_start = time.time()
            
            while chunks_completed + len(chunks_failed) < self.num_connections:
                if self.is_cancelled:
                    for downloader in self.chunk_downloaders:
                        downloader.is_cancelled = True
                    self.signals.status.emit(self.download_id, "Cancelled")
                    self._cleanup_temp_files(temp_path)
                    return
                
                # Update pause state for all chunk downloaders
                for downloader in self.chunk_downloaders:
                    downloader.is_paused = self.is_paused
                
                # Check for completed chunks
                try:
                    chunk_id, success, message = chunk_queue.get(timeout=0.5)
                    if success:
                        chunks_completed += 1
                    else:
                        chunks_failed.append((chunk_id, message))
                        self.signals.status.emit(self.download_id, f"Chunk {chunk_id} failed: {message}")
                except queue.Empty:
                    # No completed chunks in this cycle, just update progress
                    pass
                
                # Update progress
                current_time = time.time()
                if current_time - start_time >= 0.5:
                    with download_tracker.lock:
                        progress = int((download_tracker.total_downloaded / total_size) * 100)
                        speed_str = self.format_size(download_tracker.current_speed) + "/s"
                        downloaded_str = f"{self.format_size(download_tracker.total_downloaded)} / {self.format_size(total_size)}"
                        self.signals.progress.emit(self.download_id, progress, speed_str, downloaded_str)
                    start_time = current_time
            
            # All chunks completed or failed
            if chunks_failed:
                total_failed = len(chunks_failed)
                self.signals.status.emit(self.download_id, f"Download failed: {total_failed} chunks could not be downloaded")
                self._cleanup_temp_files(temp_path)
                return
            
            # Merge chunks
            self.signals.status.emit(self.download_id, "Merging downloaded chunks...")
            self._merge_chunks(temp_path, full_path, self.num_connections)
            
            # Calculate final statistics
            total_time = time.time() - download_start
            avg_speed = total_size / total_time if total_time > 0 else 0
            avg_speed_str = self.format_size(avg_speed) + "/s"
            downloaded_str = f"{self.format_size(total_size)} / {self.format_size(total_size)}"
            
            self.signals.progress.emit(self.download_id, 100, avg_speed_str, downloaded_str)
            self.signals.status.emit(self.download_id, "Completed")
            self.signals.completed.emit(self.download_id)
            
        except requests.exceptions.RequestException as e:
            if self.is_cancelled:
                self.signals.status.emit(self.download_id, "Cancelled")
            else:
                self.signals.status.emit(self.download_id, f"Error: {str(e)}")
            self._cleanup_temp_files(temp_path)
    
    def _cleanup_temp_files(self, temp_path):
        # Clean up partial files
        for i in range(self.num_connections):
            part_file = f"{temp_path}.part{i}"
            if os.path.exists(part_file):
                try:
                    os.remove(part_file)
                except:
                    pass
    
    def _merge_chunks(self, temp_path, output_path, num_chunks):
        with open(output_path, 'wb') as outfile:
            for i in range(num_chunks):
                part_file = f"{temp_path}.part{i}"
                if os.path.exists(part_file):
                    with open(part_file, 'rb') as infile:
                        outfile.write(infile.read())
                    try:
                        os.remove(part_file)  # Delete part file after merging
                    except:
                        pass
    
    def pause(self):
        self.is_paused = True
        self.signals.status.emit(self.download_id, "Paused")
    
    def resume(self):
        self.is_paused = False
        self.signals.status.emit(self.download_id, "Downloading...")
    
    def cancel(self):
        self.is_cancelled = True
    
    @staticmethod
    def format_size(size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes:.2f} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.2f} MB"
        else:
            return f"{size_bytes/(1024*1024*1024):.2f} GB"


class DownloadItem(QWidget):
    def __init__(self, download_id, url, save_path, num_connections=DEFAULT_CONNECTIONS, parent=None):
        super().__init__(parent)
        self.download_id = download_id
        self.url = url
        self.save_path = save_path
        self.num_connections = num_connections
        self.download_thread = None
        self.signals = DownloadSignals()
        
        self.initUI()
        self.connectSignals()
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(0)
        
        # Container with background
        container = QFrame(self)
        container.setObjectName("downloadItemFrame")
        container.setStyleSheet(f"""
            #downloadItemFrame {{
                background-color: {DARK_SECONDARY};
                border-radius: 8px;
            }}
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(15, 15, 15, 15)
        container_layout.setSpacing(12)
        
        # Top row: filename and control buttons
        top_row = QHBoxLayout()
        
        self.file_name = QLabel(os.path.basename(urlparse(self.url).path) or translations.get_text("download"))
        self.file_name.setFont(QFont("Arial", 11, QFont.Bold))
        self.file_name.setStyleSheet(f"color: {TEXT_COLOR};")
        top_row.addWidget(self.file_name)
        
        self.conn_label = QLabel(f"({self.num_connections} {translations.get_text('connections')})")
        self.conn_label.setStyleSheet(f"color: {ACCENT_COLOR}; font-size: 10pt;")
        top_row.addWidget(self.conn_label)
        
        top_row.addStretch()
        
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)
        
        self.btn_pause_resume = QPushButton(translations.get_text("pause"))
        self.btn_pause_resume.setFixedWidth(80)
        self.btn_pause_resume.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_TERTIARY};
                color: {TEXT_COLOR};
                border-radius: 6px;
                padding: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_COLOR};
            }}
            QPushButton:disabled {{
                background-color: {DISABLED_COLOR};
                color: #aaaaaa;
            }}
        """)
        self.btn_pause_resume.clicked.connect(self.toggle_pause_resume)
        button_layout.addWidget(self.btn_pause_resume)
        
        self.btn_cancel = QPushButton(translations.get_text("cancel"))
        self.btn_cancel.setFixedWidth(80)
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_TERTIARY};
                color: {TEXT_COLOR};
                border-radius: 6px;
                padding: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #E74C3C;
            }}
            QPushButton:disabled {{
                background-color: {DISABLED_COLOR};
                color: #aaaaaa;
            }}
        """)
        self.btn_cancel.clicked.connect(self.cancel_download)
        button_layout.addWidget(self.btn_cancel)
        
        top_row.addWidget(button_container)
        
        container_layout.addLayout(top_row)
        
        # URL and path info in collapsible section
        info_container = QFrame()
        info_container.setStyleSheet(f"""
            background-color: {DARK_TERTIARY};
            border-radius: 6px;
            padding: 8px;
        """)
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setSpacing(5)
        
        # URL row
        url_row = QHBoxLayout()
        url_label = QLabel(translations.get_text("address") + ":")
        url_label.setFixedWidth(40)
        url_label.setStyleSheet(f"color: {TEXT_COLOR}; font-weight: bold;")
        url_row.addWidget(url_label)
        
        self.url_display = QLabel(self.url)
        self.url_display.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.url_display.setStyleSheet(f"color: {TEXT_COLOR}; font-size: 9pt;")
        self.url_display.setWordWrap(True)
        url_row.addWidget(self.url_display)
        
        info_layout.addLayout(url_row)
        
        # Path row
        path_row = QHBoxLayout()
        path_label = QLabel(translations.get_text("path") + ":")
        path_label.setFixedWidth(40)
        path_label.setStyleSheet(f"color: {TEXT_COLOR}; font-weight: bold;")
        path_row.addWidget(path_label)
        
        self.path_display = QLabel(self.save_path)
        self.path_display.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.path_display.setStyleSheet(f"color: {TEXT_COLOR}; font-size: 9pt;")
        self.path_display.setWordWrap(True)
        path_row.addWidget(self.path_display)
        
        info_layout.addLayout(path_row)
        
        container_layout.addWidget(info_container)
        
        # Progress bar with more modern style
        progress_container = QFrame()
        progress_container.setStyleSheet("background-color: transparent;")
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 5, 0, 0)
        progress_layout.setSpacing(8)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: {DARK_TERTIARY};
                height: 10px;
                text-align: center;
                color: {TEXT_COLOR};
                font-weight: bold;
            }}
            
            QProgressBar::chunk {{
                background-color: {PROGRESS_COLOR};
                border-radius: 4px;
            }}
        """)
        progress_layout.addWidget(self.progress_bar)
        
        # Stats row with modern icons
        stats_row = QHBoxLayout()
        
        self.status_label = QLabel(translations.get_text("waiting"))
        self.status_label.setStyleSheet(f"color: {TEXT_COLOR};")
        stats_row.addWidget(self.status_label)
        
        stats_row.addStretch()
        
        self.size_label = QLabel("0 KB / 0 KB")
        self.size_label.setStyleSheet(f"color: {TEXT_COLOR};")
        stats_row.addWidget(self.size_label)
        
        stats_row.addSpacing(15)
        
        self.speed_label = QLabel("0 KB/s")
        self.speed_label.setStyleSheet(f"color: {TEXT_COLOR};")
        stats_row.addWidget(self.speed_label)
        
        progress_layout.addLayout(stats_row)
        
        container_layout.addWidget(progress_container)
        
        # Add container to main layout
        layout.addWidget(container)
        
        # Set main layout
        self.setLayout(layout)
    
    def connectSignals(self):
        self.signals.progress.connect(self.update_progress)
        self.signals.status.connect(self.update_status)
        self.signals.completed.connect(self.download_completed)
    
    def start_download(self):
        self.download_thread = DownloadThread(
            self.url, 
            self.save_path, 
            self.download_id, 
            self.signals,
            self.num_connections
        )
        self.download_thread.start()
        
    def update_progress(self, download_id, progress, speed, size_info):
        if download_id == self.download_id:
            self.progress_bar.setValue(progress)
            self.speed_label.setText(speed)
            self.size_label.setText(size_info)
    
    def update_status(self, download_id, status):
        if download_id == self.download_id:
            # Translate common status messages
            translated_status = status
            if status == "Paused":
                translated_status = translations.get_text("pause")
                self.btn_pause_resume.setText(translations.get_text("resume"))
            elif status in ["Downloading...", "Resuming download..."]:
                translated_status = translations.get_text("download") + "..."
                self.btn_pause_resume.setText(translations.get_text("pause"))
            elif status == "Completed":
                translated_status = translations.get_text("completed")
            elif status == "Waiting...":
                translated_status = translations.get_text("waiting")
            elif status == "Cancelled":
                translated_status = translations.get_text("cancel")
                
            self.status_label.setText(translated_status)
            
            # Update button text and progress bar color based on status
            if status == "Paused":
                self.progress_bar.setStyleSheet(f"""
                    QProgressBar {{
                        border: 1px solid #555555;
                        border-radius: 3px;
                        background-color: {DARK_TERTIARY};
                        height: 15px;
                        text-align: center;
                        color: {TEXT_COLOR};
                        font-weight: bold;
                    }}
                    
                    QProgressBar::chunk {{
                        background-color: #f39c12;
                        border-radius: 2px;
                    }}
                """)
            elif status in ["Downloading...", "Resuming download..."]:
                self.progress_bar.setStyleSheet(f"""
                    QProgressBar {{
                        border: 1px solid #555555;
                        border-radius: 3px;
                        background-color: {DARK_TERTIARY};
                        height: 15px;
                        text-align: center;
                        color: {TEXT_COLOR};
                        font-weight: bold;
                    }}
                    
                    QProgressBar::chunk {{
                        background-color: {PROGRESS_COLOR};
                        border-radius: 2px;
                    }}
                """)
            elif status == "Completed":
                self.progress_bar.setStyleSheet(f"""
                    QProgressBar {{
                        border: 1px solid #555555;
                        border-radius: 3px;
                        background-color: {DARK_TERTIARY};
                        height: 15px;
                        text-align: center;
                        color: {TEXT_COLOR};
                        font-weight: bold;
                    }}
                    
                    QProgressBar::chunk {{
                        background-color: #3498db;
                        border-radius: 2px;
                    }}
                """)
            
            # Disable buttons when completed or cancelled
            if status in ["Completed", "Cancelled"]:
                self.btn_pause_resume.setEnabled(False)
                self.btn_cancel.setEnabled(False)
    
    def download_completed(self, download_id):
        if download_id == self.download_id:
            # Already handled in update_status
            pass
    
    def toggle_pause_resume(self):
        if not self.download_thread:
            return
            
        if self.download_thread.is_paused:
            self.download_thread.resume()
            self.btn_pause_resume.setText("Pause")
        else:
            self.download_thread.pause()
            self.btn_pause_resume.setText("Resume")
    
    def cancel_download(self):
        if self.download_thread:
            self.download_thread.cancel()


class DownloadManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.download_items = {}
        self.download_counter = 0
        self.num_connections = DEFAULT_CONNECTIONS
        self.database = Database()  # Initialize database
        self.notification_manager = NotificationManager(app_name="FlashGet")  # Initialize notification manager
        
        # Load language from database
        saved_language = self.database.get_setting('language', translations.DEFAULT_LANGUAGE)
        if saved_language and saved_language in translations.TRANSLATIONS:
            translations.set_language(saved_language)
        
        # Set window flags for frameless window
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Variables for window dragging
        self.dragging = False
        self.offset = QPoint()
        
        self.initUI()
        self.setDarkTheme()
    
    def initUI(self):
        self.setWindowTitle("FlashGet")
        self.setGeometry(100, 100, 750, 600)  # Larger window for better spacing
        
        # Create main container with border and shadow
        self.main_container = QFrame(self)
        self.main_container.setObjectName("mainContainer")
        self.main_container.setStyleSheet(f"""
            #mainContainer {{
                background-color: {DARK_PRIMARY};
                border-radius: 10px;
                border: 1px solid {DARK_TERTIARY};
            }}
        """)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 0)
        self.main_container.setGraphicsEffect(shadow)
        
        # Main layout for the container
        container_layout = QVBoxLayout(self.main_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Custom title bar
        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setStyleSheet(f"""
            #titleBar {{
                background-color: {DARK_PRIMARY};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
        """)
        title_bar.setFixedHeight(40)
        title_bar.mousePressEvent = self.title_bar_mouse_press
        title_bar.mouseMoveEvent = self.title_bar_mouse_move
        title_bar.mouseReleaseEvent = self.title_bar_mouse_release
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 15, 0)
        
        app_title = QLabel("FlashGet")
        app_title.setStyleSheet(f"""
            color: {TEXT_COLOR};
            font-size: 18px;
            font-weight: bold;
        """)
        title_layout.addWidget(app_title)
        
        title_layout.addStretch()
        
        # Language selector in title bar
        self.language_selector = QComboBox()
        self.language_selector.setFixedWidth(120)
        self.language_selector.setStyleSheet(f"""
            QComboBox {{
                background-color: {DARK_TERTIARY};
                color: {TEXT_COLOR};
                border: none;
                border-radius: 5px;
                padding: 5px;
                min-height: 25px;
            }}
            QComboBox::drop-down {{
                width: 20px;
                border: none;
                background: {DARK_TERTIARY};
            }}
            QComboBox QAbstractItemView {{
                background-color: {DARK_SECONDARY};
                color: {TEXT_COLOR};
                selection-background-color: {ACCENT_COLOR};
                selection-color: {TEXT_COLOR};
                border: none;
                outline: none;
            }}
        """)
        
        # Fill language selector
        for lang_code, lang_name in translations.get_available_languages():
            self.language_selector.addItem(lang_name, lang_code)
            
        # Set current language in UI
        current_lang = translations.current_language
        for i in range(self.language_selector.count()):
            if self.language_selector.itemData(i) == current_lang:
                self.language_selector.setCurrentIndex(i)
                break
                
        # Connect language change signal
        self.language_selector.currentIndexChanged.connect(self.change_language)
        
        title_layout.addWidget(self.language_selector)
        title_layout.addSpacing(10)
        
        # Window control buttons
        btn_minimize = QPushButton("—")
        btn_minimize.setFixedSize(30, 30)
        btn_minimize.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_PRIMARY};
                color: {TEXT_COLOR};
                border: none;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {DARK_TERTIARY};
                border-radius: 15px;
            }}
        """)
        btn_minimize.clicked.connect(self.showMinimized)
        
        btn_close = QPushButton("×")
        btn_close.setFixedSize(30, 30)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_PRIMARY};
                color: {TEXT_COLOR};
                border: none;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_COLOR};
                border-radius: 15px;
            }}
        """)
        btn_close.clicked.connect(self.close)
        
        title_layout.addWidget(btn_minimize)
        title_layout.addWidget(btn_close)
        
        container_layout.addWidget(title_bar)
        
        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)
        
        # App header with logo and title
        header_container = QFrame()
        header_container.setObjectName("headerContainer")
        header_container.setStyleSheet(f"""
            #headerContainer {{
                background-color: {DARK_PRIMARY};
                border-radius: 8px;
                padding: 0px;
            }}
        """)
        header_container.setMaximumHeight(60)
        
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        app_title = QLabel("FlashGet")
        app_title.setStyleSheet(f"""
            color: {TEXT_COLOR};
            font-size: 18px;
            font-weight: bold;
        """)
        header_layout.addWidget(app_title)
        
        header_layout.addStretch()
        
        # Create an elegant toolbar with icons
        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(12)
        
        # Settings button with icon
        self.settings_btn = QPushButton(translations.get_text("settings"))
        self.settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_TERTIARY};
                color: {TEXT_COLOR};
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_COLOR};
            }}
        """)
        self.settings_btn.clicked.connect(self.open_settings)
        toolbar_layout.addWidget(self.settings_btn)
        
        # History button with icon
        self.history_btn = QPushButton(translations.get_text("history"))
        self.history_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_TERTIARY};
                color: {TEXT_COLOR};
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_COLOR};
            }}
        """)
        self.history_btn.clicked.connect(self.show_history)
        toolbar_layout.addWidget(self.history_btn)
        
        # Cloud Services button
        self.cloud_btn = QPushButton(translations.get_text("cloud_services"))
        self.cloud_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_TERTIARY};
                color: {TEXT_COLOR};
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_COLOR};
            }}
        """)
        self.cloud_btn.clicked.connect(self.open_cloud_services)
        toolbar_layout.addWidget(self.cloud_btn)
        
        # Notifications button
        self.notif_btn = QPushButton(translations.get_text("notifications"))
        self.notif_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_TERTIARY};
                color: {TEXT_COLOR};
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_COLOR};
            }}
        """)
        self.notif_btn.clicked.connect(self.manage_notifications)
        toolbar_layout.addWidget(self.notif_btn)
        
        header_layout.addWidget(toolbar_widget)
        
        content_layout.addWidget(header_container)
        
        # URL input and buttons in an elegant card
        input_container = QFrame()
        input_container.setObjectName("inputContainer")
        input_container.setStyleSheet(f"""
            #inputContainer {{
                background-color: {DARK_SECONDARY};
                border-radius: 10px;
                padding: 0px;
            }}
        """)
        
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(20, 20, 20, 20)
        input_layout.setSpacing(15)
        
        # URL input with icon
        url_container = QFrame()
        url_container.setStyleSheet(f"""
            background-color: {DARK_TERTIARY};
            border-radius: 8px;
        """)
        url_layout = QHBoxLayout(url_container)
        url_layout.setContentsMargins(12, 0, 12, 0)
        
        url_label = QLabel(translations.get_text("url") + ":")
        url_label.setObjectName("url_label")
        url_label.setStyleSheet(f"color: {TEXT_COLOR}; font-weight: bold;")
        url_layout.addWidget(url_label)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(translations.get_text("url_placeholder"))
        self.url_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: transparent;
                color: {TEXT_COLOR};
                border: none;
                padding: 12px 5px;
                font-size: 13px;
            }}
        """)
        url_layout.addWidget(self.url_input, 1)
        
        input_layout.addWidget(url_container)
        
        # Save location with icon
        save_container = QFrame()
        save_container.setStyleSheet(f"""
            background-color: {DARK_TERTIARY};
            border-radius: 8px;
        """)
        save_layout = QHBoxLayout(save_container)
        save_layout.setContentsMargins(12, 0, 12, 0)
        
        save_label = QLabel(translations.get_text("save_to") + ":")
        save_label.setObjectName("save_label")
        save_label.setStyleSheet(f"color: {TEXT_COLOR}; font-weight: bold;")
        save_layout.addWidget(save_label)
        
        self.save_path_input = QLineEdit()
        self.save_path_input.setPlaceholderText(translations.get_text("save_to_placeholder"))
        self.save_path_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: transparent;
                color: {TEXT_COLOR};
                border: none;
                padding: 12px 5px;
                font-size: 13px;
            }}
        """)
        # Default to Downloads folder
        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.save_path_input.setText(downloads_path)
        save_layout.addWidget(self.save_path_input, 1)
        
        self.browse_btn = QPushButton(translations.get_text("browse"))
        self.browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_PRIMARY};
                color: {TEXT_COLOR};
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_COLOR};
            }}
        """)
        self.browse_btn.clicked.connect(self.select_save_location)
        save_layout.addWidget(self.browse_btn)
        
        input_layout.addWidget(save_container)
        
        # Connection settings with slider
        conn_container = QFrame()
        conn_container.setStyleSheet(f"""
            background-color: {DARK_TERTIARY};
            border-radius: 8px;
            padding: 8px;
        """)
        conn_layout = QHBoxLayout(conn_container)
        conn_layout.setContentsMargins(12, 6, 12, 6)
        
        conn_label = QLabel(translations.get_text("connections") + ":")
        conn_label.setObjectName("conn_label")
        conn_label.setStyleSheet(f"color: {TEXT_COLOR}; font-weight: bold;")
        conn_layout.addWidget(conn_label)
        
        self.conn_slider = QSlider(Qt.Horizontal)
        self.conn_slider.setMinimum(1)
        self.conn_slider.setMaximum(MAX_CONNECTIONS)
        self.conn_slider.setValue(DEFAULT_CONNECTIONS)
        self.conn_slider.setTickInterval(1)
        self.conn_slider.setTickPosition(QSlider.TicksBelow)
        self.conn_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 8px;
                background: {DARK_PRIMARY};
                margin: 2px 0;
                border-radius: 4px;
            }}

            QSlider::handle:horizontal {{
                background: {ACCENT_COLOR};
                border: none;
                width: 18px;
                height: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }}
            
            QSlider::handle:horizontal:hover {{
                background: #ff5b76;
            }}
            
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 {ACCENT_COLOR}, stop: 1 #ff5b76);
                height: 8px;
                border-radius: 4px;
            }}
        """)
        self.conn_slider.valueChanged.connect(self.update_connections)
        conn_layout.addWidget(self.conn_slider, 1)
        
        self.conn_value = QLabel(f"{DEFAULT_CONNECTIONS}")
        self.conn_value.setStyleSheet(f"color: {TEXT_COLOR}; min-width: 25px; text-align: center;")
        conn_layout.addWidget(self.conn_value)
        
        input_layout.addWidget(conn_container)
        
        # Download button - centered and prominent
        btn_container = QFrame()
        btn_container.setStyleSheet("background-color: transparent;")
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 10, 0, 10)
        
        btn_layout.addStretch()
        
        self.download_btn = QPushButton("شروع دانلود")
        self.download_btn.setMinimumWidth(150)
        self.download_btn.setMinimumHeight(45)
        self.download_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_COLOR};
                color: white;
                border-radius: 8px;
                padding: 12px 20px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #ff5b76;
            }}
        """)
        self.download_btn.clicked.connect(self.add_download)
        btn_layout.addWidget(self.download_btn)
        
        btn_layout.addStretch()
        
        input_layout.addWidget(btn_container)
        
        content_layout.addWidget(input_container)
        
        # Downloads section header
        downloads_header_container = QFrame()
        downloads_header_container.setStyleSheet("background-color: transparent;")
        downloads_header_layout = QHBoxLayout(downloads_header_container)
        downloads_header_layout.setContentsMargins(5, 5, 5, 5)
        
        downloads_header = QLabel(translations.get_text("active_downloads"))
        downloads_header.setObjectName("downloads_header")
        downloads_header.setStyleSheet(f"""
            color: {TEXT_COLOR}; 
            font-size: 16px; 
            font-weight: bold;
        """)
        downloads_header_layout.addWidget(downloads_header)
        
        downloads_header_layout.addStretch()
        
        content_layout.addWidget(downloads_header_container)
        
        # Downloads list with better styling
        downloads_container = QFrame()
        downloads_container.setObjectName("downloadsContainer")
        downloads_container.setStyleSheet(f"""
            #downloadsContainer {{
                background-color: {DARK_SECONDARY};
                border-radius: 10px;
            }}
        """)
        downloads_layout = QVBoxLayout(downloads_container)
        downloads_layout.setContentsMargins(15, 15, 15, 15)
        
        self.downloads_list = QListWidget()
        self.downloads_list.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                color: {TEXT_COLOR};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                border: none;
                padding: 4px;
            }}
        """)
        self.downloads_list.setSelectionMode(QListWidget.NoSelection)
        self.downloads_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.downloads_list.customContextMenuRequested.connect(self.show_context_menu)
        self.downloads_list.setIconSize(QSize(32, 32))
        downloads_layout.addWidget(self.downloads_list)
        
        content_layout.addWidget(downloads_container, 1)
        
        # Status bar at the bottom
        status_container = QFrame()
        status_container.setMaximumHeight(30)
        status_container.setStyleSheet(f"""
            background-color: {DARK_PRIMARY};
            border-radius: 6px;
        """)
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(15, 0, 15, 0)
        
        self.status_label = QLabel("آماده برای دانلود")
        self.status_label.setStyleSheet(f"color: {TEXT_COLOR};")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.version_label = QLabel(f"نسخه: 1.0")
        self.version_label.setStyleSheet(f"color: {TEXT_COLOR};")
        status_layout.addWidget(self.version_label)
        
        content_layout.addWidget(status_container)
        
        container_layout.addWidget(content_widget)
        
        # Set the main container as the central widget
        self.setCentralWidget(self.main_container)
        
    def title_bar_mouse_press(self, event):
        """Handle mouse press events for custom title bar"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()
    
    def title_bar_mouse_move(self, event):
        """Handle mouse move events for custom title bar"""
        if self.dragging and self.offset is not None:
            self.move(self.mapToGlobal(event.pos() - self.offset))
    
    def title_bar_mouse_release(self, event):
        """Handle mouse release events for custom title bar"""
        self.dragging = False

    def update_connections(self, value):
        self.num_connections = value
        self.conn_value.setText(f"{value}")
    
    def setDarkTheme(self):
        # Set the dark theme for the entire application
        app = QApplication.instance()
        app.setStyle(QStyleFactory.create("Fusion"))
        
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(DARK_PRIMARY))
        dark_palette.setColor(QPalette.WindowText, QColor(TEXT_COLOR))
        dark_palette.setColor(QPalette.Base, QColor(DARK_SECONDARY))
        dark_palette.setColor(QPalette.AlternateBase, QColor(DARK_TERTIARY))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(TEXT_COLOR))
        dark_palette.setColor(QPalette.ToolTipText, QColor(TEXT_COLOR))
        dark_palette.setColor(QPalette.Text, QColor(TEXT_COLOR))
        dark_palette.setColor(QPalette.Button, QColor(DARK_SECONDARY))
        dark_palette.setColor(QPalette.ButtonText, QColor(TEXT_COLOR))
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(ACCENT_COLOR))
        dark_palette.setColor(QPalette.Highlight, QColor(ACCENT_COLOR))
        dark_palette.setColor(QPalette.HighlightedText, QColor(TEXT_COLOR))
        
        app.setPalette(dark_palette)
        
        # Additional stylesheet for the application
        app.setStyleSheet(f"""
            QToolTip {{ 
                border: 1px solid #555555; 
                background-color: {DARK_TERTIARY}; 
                color: {TEXT_COLOR}; 
                padding: 5px;
                opacity: 200; 
            }}
            QMenu {{
                background-color: {DARK_SECONDARY};
                color: {TEXT_COLOR};
                border: 1px solid #555555;
            }}
            QMenu::item {{
                padding: 5px 30px 5px 20px;
            }}
            QMenu::item:selected {{
                background-color: {ACCENT_COLOR};
            }}
        """)
    
    def select_save_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Location")
        if folder:
            self.save_path_input.setText(folder)
    
    def add_download(self):
        url = self.url_input.text().strip()
        save_path = self.save_path_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a URL")
            return
            
        if not save_path or not os.path.isdir(save_path):
            QMessageBox.warning(self, "Error", "Please select a valid save location")
            return
        
        try:
            # Test if URL is valid
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
        except Exception:
            QMessageBox.warning(self, "Error", "Please enter a valid URL")
            return
        
        # Create download item
        download_id = f"download_{self.download_counter}"
        self.download_counter += 1
        
        download_item = DownloadItem(download_id, url, save_path, self.num_connections)
        
        # Create list item and add widget
        list_item = QListWidgetItem()
        self.downloads_list.addItem(list_item)
        list_item.setSizeHint(download_item.sizeHint())
        self.downloads_list.setItemWidget(list_item, download_item)
        
        # Store references
        self.download_items[download_id] = {
            "widget": download_item,
            "list_item": list_item
        }
        
        # Start download
        download_item.start_download()
        
        # Clear URL input
        self.url_input.clear()
    
    def show_context_menu(self, position):
        item = self.downloads_list.itemAt(position)
        if not item:
            return
            
        download_widget = self.downloads_list.itemWidget(item)
        
        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {DARK_SECONDARY};
                color: {TEXT_COLOR};
                border: 1px solid #555555;
            }}
            QMenu::item {{
                padding: 5px 30px 5px 20px;
            }}
            QMenu::item:selected {{
                background-color: {ACCENT_COLOR};
            }}
        """)
        
        open_folder_action = menu.addAction("Open Folder")
        open_folder_action.triggered.connect(
            lambda: os.startfile(download_widget.save_path))
        
        action = menu.exec_(self.downloads_list.mapToGlobal(position))

    # Add methods for handling toolbar buttons
    def open_settings(self):
        from settings_dialog import SettingsDialog
        settings_dialog = SettingsDialog(self)
        if settings_dialog.exec_():
            # Reload settings if needed
            self.num_connections = self.database.get_setting('default_connections', DEFAULT_CONNECTIONS)
            self.conn_slider.setValue(self.num_connections)
            
            # Update UI theme if changed
            theme = self.database.get_setting('theme', 'dark')
            if theme == 'dark':
                self.setDarkTheme()
                
            # Update language if needed
            lang = self.database.get_setting('language', translations.DEFAULT_LANGUAGE)
            if lang != translations.current_language:
                translations.set_language(lang)
                self.update_ui_text()
                
                # Update language selector
                for i in range(self.language_selector.count()):
                    if self.language_selector.itemData(i) == lang:
                        self.language_selector.setCurrentIndex(i)
                        break
    
    def show_history(self):
        downloads = self.database.get_download_history(limit=50)
        if not downloads:
            QMessageBox.information(self, "Download History", "No download history found.")
            return
            
        history_text = "Download History:\n\n"
        for download in downloads:
            status = download.get('status', 'Unknown')
            filename = download.get('file_name', 'Unknown')
            size = utils.format_size(download.get('file_size', 0)) if download.get('file_size') else 'Unknown'
            date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(download.get('start_time', 0)))
            
            history_text += f"{filename} - {size} - {status} - {date}\n"
            
        QMessageBox.information(self, "Download History", history_text)
    
    def open_cloud_services(self):
        QMessageBox.information(self, "Cloud Services", "Cloud Services functionality will be implemented.")
        # In the full implementation, this would open a cloud services dialog
    
    def manage_notifications(self):
        QMessageBox.information(self, "Notifications", "Notification settings will be implemented.")
        # In the full implementation, this would open a notification settings dialog

    def change_language(self, index):
        lang_code = self.language_selector.itemData(index)
        if translations.set_language(lang_code):
            # Save language preference to database
            self.database.set_setting('language', lang_code)
            
            # Update UI text immediately
            self.update_ui_text()
            
            # Notify the user
            QMessageBox.information(self, "FlashGet", translations.get_text("language_changed"))
    
    def update_ui_text(self):
        """Update all UI elements with translated text"""
        # Update toolbar buttons
        self.settings_btn.setText(translations.get_text("settings"))
        self.history_btn.setText(translations.get_text("history"))
        self.cloud_btn.setText(translations.get_text("cloud_services"))
        self.notif_btn.setText(translations.get_text("notifications"))
        
        # URL input area
        url_label = self.findChild(QLabel, "url_label")
        if url_label:
            url_label.setText(translations.get_text("url") + ":")
        self.url_input.setPlaceholderText(translations.get_text("url_placeholder"))
        
        # Save location area
        save_label = self.findChild(QLabel, "save_label")
        if save_label:
            save_label.setText(translations.get_text("save_to") + ":")
        self.save_path_input.setPlaceholderText(translations.get_text("save_to_placeholder"))
        self.browse_btn.setText(translations.get_text("browse"))
        
        # Connection slider area
        conn_label = self.findChild(QLabel, "conn_label")
        if conn_label:
            conn_label.setText(translations.get_text("connections") + ":")
        
        # Download button
        self.download_btn.setText(translations.get_text("start_download"))
        
        # Downloads header
        downloads_header = self.findChild(QLabel, "downloads_header")
        if downloads_header:
            downloads_header.setText(translations.get_text("active_downloads"))
        
        # Status bar
        self.status_label.setText(translations.get_text("ready"))
        self.version_label.setText(f"{translations.get_text('version')}: 1.0")
        
        # We need to update dynamically created download items too
        for download_id, download_data in self.download_items.items():
            download_widget = download_data.get("widget")
            if download_widget:
                # Update buttons in download widget
                if hasattr(download_widget, "btn_pause_resume"):
                    if download_widget.download_thread and download_widget.download_thread.is_paused:
                        download_widget.btn_pause_resume.setText(translations.get_text("resume"))
                    else:
                        download_widget.btn_pause_resume.setText(translations.get_text("pause"))
                
                if hasattr(download_widget, "btn_cancel"):
                    download_widget.btn_cancel.setText(translations.get_text("cancel"))
                
                # Update labels in download widget
                if hasattr(download_widget, "status_label") and hasattr(download_widget, "download_thread"):
                    # Only update if it's a standard status
                    current_status = download_widget.status_label.text()
                    if current_status in ["در انتظار...", "Waiting...", "等待中...", "في الانتظار..."]:
                        download_widget.status_label.setText(translations.get_text("waiting"))

def main():
    app = QApplication(sys.argv)
    
    # Set up RTL support for Persian
    app.setLayoutDirection(Qt.RightToLeft)
    
    window = DownloadManager()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 