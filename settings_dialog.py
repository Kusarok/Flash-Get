import os
import sys
from PyQt5.QtWidgets import (QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, QWidget,
                          QLabel, QLineEdit, QCheckBox, QSpinBox, QComboBox,
                          QPushButton, QFileDialog, QFormLayout, QGroupBox,
                          QRadioButton, QSlider, QMessageBox, QScrollArea, QFrame)
from PyQt5.QtCore import Qt, QSettings, QPoint
from PyQt5.QtGui import QIcon, QFont, QColor

from database import Database
import utils
import translations

# Define colors (matching downloader.py)
DARK_PRIMARY = "#1A1A2E"  # Deeper blue-black
DARK_SECONDARY = "#16213E"  # Deep blue
DARK_TERTIARY = "#0F3460"  # Rich blue
ACCENT_COLOR = "#E94560"  # Vibrant red accent
TEXT_COLOR = "#F0F0F0"  # Slightly off-white
DISABLED_COLOR = "#555555"
PROGRESS_COLOR = "#4CAF50"  # Green
CARD_SHADOW = "0px 2px 6px rgba(0, 0, 0, 0.3)"

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translations.get_text("settings"))
        self.resize(600, 450)  # Increased size for better layout
        self.database = Database()
        
        # Set window flags for frameless window
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Variables for window dragging
        self.dragging = False
        self.offset = QPoint()
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DARK_PRIMARY};
                color: {TEXT_COLOR};
            }}
            QTabWidget::pane {{
                border: none;
                background-color: {DARK_SECONDARY};
                border-radius: 8px;
            }}
            QTabBar {{
                alignment: center;
            }}
            QTabBar::tab {{
                background-color: {DARK_TERTIARY};
                color: {TEXT_COLOR};
                padding: 10px 5px;
                min-width: 135px;
                max-width: 135px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                margin-right: 2px;
                margin-left: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {DARK_SECONDARY};
                border-bottom: 3px solid {ACCENT_COLOR};
            }}
            QLabel {{
                color: {TEXT_COLOR};
            }}
            QLineEdit, QSpinBox, QComboBox {{
                background-color: {DARK_TERTIARY};
                color: {TEXT_COLOR};
                border: none;
                border-radius: 5px;
                padding: 8px;
                selection-background-color: {ACCENT_COLOR};
                min-height: 18px;
            }}
            QSpinBox {{
                min-width: 80px;
                max-width: 150px;
            }}
            QComboBox {{
                min-width: 150px;
            }}
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
                border: 1px solid {ACCENT_COLOR};
            }}
            QCheckBox {{
                color: {TEXT_COLOR};
                padding: 5px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 3px;
                background-color: {DARK_TERTIARY};
            }}
            QCheckBox::indicator:checked {{
                background-color: {ACCENT_COLOR};
                image: url(check.png);
            }}
            QPushButton {{
                background-color: {DARK_TERTIARY};
                color: {TEXT_COLOR};
                border-radius: 6px;
                padding: 10px 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_COLOR};
            }}
            QPushButton#primaryButton {{
                background-color: {ACCENT_COLOR};
                color: white;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton#primaryButton:hover {{
                background-color: #ff5b76;
            }}
            QGroupBox {{
                color: {TEXT_COLOR};
                border: 1px solid #444;
                border-radius: 6px;
                margin-top: 15px;
                padding-top: 22px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                left: 7px;
            }}
            QRadioButton {{
                color: {TEXT_COLOR};
                padding: 5px;
            }}
            QRadioButton::indicator {{
                width: 15px;
                height: 15px;
                border-radius: 7px;
                background-color: {DARK_TERTIARY};
            }}
            QRadioButton::indicator:checked {{
                background-color: {ACCENT_COLOR};
                border: 3px solid {DARK_TERTIARY};
                width: 9px;
                height: 9px;
            }}
            QSlider::groove:horizontal {{
                height: 8px;
                background: {DARK_TERTIARY};
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
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {DARK_PRIMARY};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {DARK_TERTIARY};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {ACCENT_COLOR};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QFormLayout {{
                spacing: 12px;
            }}
        """)
        
        self.initUI()
        self.loadSettings()
    
    def initUI(self):
        # Create main container with border and shadow
        main_container = QFrame(self)
        main_container.setObjectName("mainContainer")
        main_container.setStyleSheet(f"""
            #mainContainer {{
                background-color: {DARK_PRIMARY};
                border-radius: 10px;
                border: 1px solid {DARK_TERTIARY};
            }}
        """)
        
        # Main layout for the container
        container_layout = QVBoxLayout(main_container)
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
        
        # Dialog title
        title_label = QLabel("FlashGet - " + translations.get_text("app_settings"))
        title_label.setStyleSheet(f"""
            color: {TEXT_COLOR};
            font-size: 16px;
            font-weight: bold;
        """)
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        # Close button
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
        btn_close.clicked.connect(self.reject)
        title_layout.addWidget(btn_close)
        
        container_layout.addWidget(title_bar)
        
        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 10, 20, 20)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        # Center the tabs
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.tabBar().setDrawBase(False)
        
        # Create tabs
        self.general_tab = QWidget()
        self.connection_tab = QWidget()
        self.notification_tab = QWidget()
        self.cloud_tab = QWidget()
        
        # Add tabs to widget
        self.tab_widget.addTab(self.general_tab, translations.get_text("general"))
        self.tab_widget.addTab(self.connection_tab, translations.get_text("connection"))
        self.tab_widget.addTab(self.notification_tab, translations.get_text("notifications"))
        self.tab_widget.addTab(self.cloud_tab, translations.get_text("cloud_services"))
        
        # Distribute the tabs evenly
        tab_width = self.width() / 4
        for i in range(self.tab_widget.count()):
            self.tab_widget.tabBar().setTabTextColor(i, QColor(TEXT_COLOR))
        
        # Setup tab contents
        self.setup_general_tab()
        self.setup_connection_tab()
        self.setup_notification_tab()
        self.setup_cloud_tab()
        
        # Add tab widget to layout
        content_layout.addWidget(self.tab_widget)
        
        # Add OK and Cancel buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 10, 0, 0)
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton(translations.get_text("cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton(translations.get_text("save"))
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.setMinimumWidth(150)
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.save_btn)
        
        content_layout.addLayout(btn_layout)
        
        container_layout.addWidget(content_widget)
        
        # Set the main layout with the container
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.addWidget(main_container)
    
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
    
    def setup_general_tab(self):
        # Create a scroll area for the general tab
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        
        # Create a widget to hold the content
        content_widget = QWidget()
        
        # Layout for the content
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(20)
        
        # Download location group
        location_group = QGroupBox(translations.get_text("download_location"))
        location_layout = QVBoxLayout(location_group)
        location_layout.setContentsMargins(15, 20, 15, 15)
        location_layout.setSpacing(15)
        
        # Use QFormLayout for better alignment
        path_form = QFormLayout()
        path_form.setLabelAlignment(Qt.AlignLeft)
        path_form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        path_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        path_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        path_form.setVerticalSpacing(10)
        path_form.setHorizontalSpacing(15)
        
        self.default_path_label = QLabel(translations.get_text("default_path"))
        self.default_path_label.setMinimumWidth(120)
        
        path_field = QWidget()
        path_field_layout = QHBoxLayout(path_field)
        path_field_layout.setContentsMargins(0, 0, 0, 0)
        path_field_layout.setSpacing(10)
        
        self.default_path_edit = QLineEdit()
        self.default_path_edit.setMinimumWidth(250)
        path_field_layout.addWidget(self.default_path_edit)
        
        self.browse_btn = QPushButton(translations.get_text("browse"))
        self.browse_btn.setFixedWidth(100)
        self.browse_btn.clicked.connect(self.browse_download_path)
        path_field_layout.addWidget(self.browse_btn)
        
        path_form.addRow(self.default_path_label, path_field)
        location_layout.addLayout(path_form)
        
        # Add a small spacer
        location_layout.addSpacing(5)
        
        self.always_ask_check = QCheckBox(translations.get_text("always_ask"))
        self.always_ask_check.setContentsMargins(5, 0, 0, 0)
        location_layout.addWidget(self.always_ask_check)
        
        layout.addWidget(location_group)
        
        # UI Settings group
        ui_group = QGroupBox(translations.get_text("ui_settings"))
        ui_layout = QVBoxLayout(ui_group)
        ui_layout.setContentsMargins(15, 20, 15, 15)
        ui_layout.setSpacing(15)
        
        # Use QFormLayout for better alignment
        ui_form = QFormLayout()
        ui_form.setLabelAlignment(Qt.AlignLeft)
        ui_form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        ui_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        ui_form.setVerticalSpacing(15)
        ui_form.setHorizontalSpacing(15)
        
        # Theme selection
        theme_label = QLabel(translations.get_text("theme"))
        theme_label.setMinimumWidth(120)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(translations.get_text("dark"), "dark")
        self.theme_combo.addItem(translations.get_text("light"), "light")
        ui_form.addRow(theme_label, self.theme_combo)
        
        # Language selection
        lang_label = QLabel(translations.get_text("language"))
        lang_label.setMinimumWidth(120)
        self.lang_combo = QComboBox()
        for code, name in translations.get_available_languages():
            self.lang_combo.addItem(name, code)
        ui_form.addRow(lang_label, self.lang_combo)
        
        ui_layout.addLayout(ui_form)
        
        # Add a small spacer
        ui_layout.addSpacing(5)
        
        # System tray option
        self.tray_check = QCheckBox(translations.get_text("system_tray"))
        self.tray_check.setContentsMargins(5, 0, 0, 0)
        ui_layout.addWidget(self.tray_check)
        
        # Start with Windows option
        self.startup_check = QCheckBox(translations.get_text("start_with_windows"))
        self.startup_check.setContentsMargins(5, 0, 0, 0)
        ui_layout.addWidget(self.startup_check)
        
        layout.addWidget(ui_group)
        
        # Behavior group
        behavior_group = QGroupBox(translations.get_text("behavior"))
        behavior_layout = QVBoxLayout(behavior_group)
        behavior_layout.setContentsMargins(15, 20, 15, 15)
        behavior_layout.setSpacing(10)
        
        self.auto_start_check = QCheckBox(translations.get_text("auto_start_queue"))
        self.auto_start_check.setContentsMargins(5, 0, 0, 0)
        behavior_layout.addWidget(self.auto_start_check)
        
        self.history_check = QCheckBox(translations.get_text("remember_history"))
        self.history_check.setContentsMargins(5, 0, 0, 0)
        behavior_layout.addWidget(self.history_check)
        
        self.shutdown_check = QCheckBox(translations.get_text("shutdown_after"))
        self.shutdown_check.setContentsMargins(5, 0, 0, 0)
        behavior_layout.addWidget(self.shutdown_check)
        
        behavior_group.setLayout(behavior_layout)
        layout.addWidget(behavior_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Set the content widget to the scroll area
        scroll_area.setWidget(content_widget)
        
        # Set the scroll area as the main widget for the tab
        tab_layout = QVBoxLayout(self.general_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll_area)
    
    def setup_connection_tab(self):
        # Create a scroll area for the connection tab
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        
        # Create a widget to hold the content
        content_widget = QWidget()
        
        # Layout for the content
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(20)
        
        # Connection settings group
        conn_group = QGroupBox(translations.get_text("connection_settings"))
        conn_layout = QVBoxLayout(conn_group)
        conn_layout.setContentsMargins(15, 20, 15, 15)
        conn_layout.setSpacing(15)
        
        # Use QFormLayout for better alignment
        conn_form = QFormLayout()
        conn_form.setLabelAlignment(Qt.AlignLeft)
        conn_form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        conn_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        conn_form.setVerticalSpacing(15)
        conn_form.setHorizontalSpacing(15)
        
        # Default connections
        default_conn_label = QLabel(translations.get_text("default_connections"))
        default_conn_label.setMinimumWidth(120)
        
        self.default_conn_spin = QSpinBox()
        self.default_conn_spin.setRange(1, 16)
        self.default_conn_spin.setValue(8)
        conn_form.addRow(default_conn_label, self.default_conn_spin)
        
        # Max connections
        max_conn_label = QLabel(translations.get_text("max_connections"))
        max_conn_label.setMinimumWidth(120)
        
        self.max_conn_spin = QSpinBox()
        self.max_conn_spin.setRange(1, 32)
        self.max_conn_spin.setValue(16)
        conn_form.addRow(max_conn_label, self.max_conn_spin)
        
        conn_layout.addLayout(conn_form)
        layout.addWidget(conn_group)
        
        # Bandwidth control group
        bandwidth_group = QGroupBox(translations.get_text("bandwidth_control"))
        bandwidth_layout = QVBoxLayout(bandwidth_group)
        bandwidth_layout.setContentsMargins(15, 20, 15, 15)
        bandwidth_layout.setSpacing(15)
        
        self.limit_bandwidth_check = QCheckBox(translations.get_text("limit_bandwidth"))
        self.limit_bandwidth_check.setContentsMargins(5, 0, 0, 0)
        self.limit_bandwidth_check.toggled.connect(self.toggle_bandwidth_limit)
        bandwidth_layout.addWidget(self.limit_bandwidth_check)
        
        # Bandwidth limit slider
        bandwidth_form = QFormLayout()
        bandwidth_form.setLabelAlignment(Qt.AlignLeft)
        bandwidth_form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        bandwidth_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        bandwidth_form.setVerticalSpacing(15)
        bandwidth_form.setHorizontalSpacing(15)
        
        limit_label = QLabel(translations.get_text("bandwidth_limit"))
        limit_label.setMinimumWidth(120)
        
        slider_widget = QWidget()
        slider_layout = QHBoxLayout(slider_widget)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(10)
        
        self.bandwidth_slider = QSlider(Qt.Horizontal)
        self.bandwidth_slider.setRange(10, 1000)
        self.bandwidth_slider.setValue(200)
        self.bandwidth_slider.setTickInterval(100)
        self.bandwidth_slider.setTickPosition(QSlider.TicksBelow)
        self.bandwidth_slider.setEnabled(False)
        slider_layout.addWidget(self.bandwidth_slider)
        
        self.bandwidth_value = QLabel("200 KB/s")
        self.bandwidth_value.setFixedWidth(80)
        slider_layout.addWidget(self.bandwidth_value)
        
        bandwidth_form.addRow(limit_label, slider_widget)
        bandwidth_layout.addLayout(bandwidth_form)
        
        layout.addWidget(bandwidth_group)
        
        # Proxy settings group
        proxy_group = QGroupBox(translations.get_text("proxy_settings"))
        proxy_layout = QVBoxLayout(proxy_group)
        proxy_layout.setContentsMargins(15, 20, 15, 15)
        proxy_layout.setSpacing(15)
        
        self.use_proxy_check = QCheckBox(translations.get_text("use_proxy"))
        self.use_proxy_check.setContentsMargins(5, 0, 0, 0)
        self.use_proxy_check.toggled.connect(self.toggle_proxy_settings)
        proxy_layout.addWidget(self.use_proxy_check)
        
        # Proxy form for better alignment
        proxy_form = QFormLayout()
        proxy_form.setLabelAlignment(Qt.AlignLeft)
        proxy_form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        proxy_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        proxy_form.setVerticalSpacing(15)
        proxy_form.setHorizontalSpacing(15)
        
        # Proxy URL
        proxy_url_label = QLabel(translations.get_text("proxy_url"))
        proxy_url_label.setMinimumWidth(120)
        
        self.proxy_url_edit = QLineEdit()
        self.proxy_url_edit.setEnabled(False)
        proxy_form.addRow(proxy_url_label, self.proxy_url_edit)
        
        proxy_layout.addLayout(proxy_form)
        
        # Proxy authentication
        self.proxy_auth_check = QCheckBox(translations.get_text("requires_auth"))
        self.proxy_auth_check.setContentsMargins(5, 0, 0, 0)
        self.proxy_auth_check.toggled.connect(self.toggle_proxy_auth)
        self.proxy_auth_check.setEnabled(False)
        proxy_layout.addWidget(self.proxy_auth_check)
        
        # Auth form
        auth_form = QFormLayout()
        auth_form.setLabelAlignment(Qt.AlignLeft)
        auth_form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        auth_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        auth_form.setVerticalSpacing(15)
        auth_form.setHorizontalSpacing(15)
        
        # Proxy username
        proxy_user_label = QLabel(translations.get_text("username"))
        proxy_user_label.setMinimumWidth(120)
        
        self.proxy_user_edit = QLineEdit()
        self.proxy_user_edit.setEnabled(False)
        auth_form.addRow(proxy_user_label, self.proxy_user_edit)
        
        # Proxy password
        proxy_pass_label = QLabel(translations.get_text("password"))
        proxy_pass_label.setMinimumWidth(120)
        
        self.proxy_pass_edit = QLineEdit()
        self.proxy_pass_edit.setEchoMode(QLineEdit.Password)
        self.proxy_pass_edit.setEnabled(False)
        auth_form.addRow(proxy_pass_label, self.proxy_pass_edit)
        
        proxy_layout.addLayout(auth_form)
        layout.addWidget(proxy_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Set the content widget to the scroll area
        scroll_area.setWidget(content_widget)
        
        # Set the scroll area as the main widget for the tab
        tab_layout = QVBoxLayout(self.connection_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll_area)
    
    def setup_notification_tab(self):
        # Create a scroll area for the notification tab
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        
        # Create a widget to hold the content
        content_widget = QWidget()
        
        # Layout for the content
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(15)
        
        # Set the content widget to the scroll area
        scroll_area.setWidget(content_widget)
        
        # Set the scroll area as the main widget for the tab
        tab_layout = QVBoxLayout(self.notification_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll_area)
        
        # Implement the rest of the notification tab content as before
        # Add notification checkboxes
        self.notify_complete_check = QCheckBox("Notify on download completion")
        layout.addWidget(self.notify_complete_check)
        
        self.notify_error_check = QCheckBox("Notify on download errors")
        layout.addWidget(self.notify_error_check)
        
        self.notify_start_check = QCheckBox("Notify on download start")
        layout.addWidget(self.notify_start_check)
        
        # Email notification group
        email_group = QGroupBox("Email Notifications")
        email_layout = QVBoxLayout()
        email_layout.setContentsMargins(15, 20, 15, 15)
        email_layout.setSpacing(15)
        
        self.email_check = QCheckBox("Send email notifications")
        self.email_check.toggled.connect(self.toggle_email_settings)
        email_layout.addWidget(self.email_check)
        
        # SMTP server settings
        smtp_layout = QHBoxLayout()
        smtp_label = QLabel("SMTP Server:")
        smtp_layout.addWidget(smtp_label)
        
        self.smtp_edit = QLineEdit()
        self.smtp_edit.setEnabled(False)
        smtp_layout.addWidget(self.smtp_edit, 1)
        
        email_layout.addLayout(smtp_layout)
        
        # Email account
        email_acc_layout = QHBoxLayout()
        email_acc_label = QLabel("Email Account:")
        email_acc_layout.addWidget(email_acc_label)
        
        self.email_acc_edit = QLineEdit()
        self.email_acc_edit.setEnabled(False)
        email_acc_layout.addWidget(self.email_acc_edit, 1)
        
        email_layout.addLayout(email_acc_layout)
        
        # Email password
        email_pass_layout = QHBoxLayout()
        email_pass_label = QLabel("Password:")
        email_pass_layout.addWidget(email_pass_label)
        
        self.email_pass_edit = QLineEdit()
        self.email_pass_edit.setEchoMode(QLineEdit.Password)
        self.email_pass_edit.setEnabled(False)
        email_pass_layout.addWidget(self.email_pass_edit, 1)
        
        email_layout.addLayout(email_pass_layout)
        
        # Recipient email
        recip_layout = QHBoxLayout()
        recip_label = QLabel("Recipient Email:")
        recip_layout.addWidget(recip_label)
        
        self.recip_edit = QLineEdit()
        self.recip_edit.setEnabled(False)
        recip_layout.addWidget(self.recip_edit, 1)
        
        email_layout.addLayout(recip_layout)
        
        # Test button
        test_email_btn = QPushButton("Test Email")
        test_email_btn.clicked.connect(self.test_email)
        test_email_btn.setEnabled(False)
        email_layout.addWidget(test_email_btn)
        
        email_group.setLayout(email_layout)
        layout.addWidget(email_group)
        
        # Telegram notification group
        telegram_group = QGroupBox("Telegram Notifications")
        telegram_layout = QVBoxLayout()
        telegram_layout.setContentsMargins(15, 20, 15, 15)
        telegram_layout.setSpacing(15)
        
        self.telegram_check = QCheckBox("Send Telegram notifications")
        self.telegram_check.toggled.connect(self.toggle_telegram_settings)
        telegram_layout.addWidget(self.telegram_check)
        
        # Bot token
        bot_layout = QHBoxLayout()
        bot_label = QLabel("Bot Token:")
        bot_layout.addWidget(bot_label)
        
        self.bot_edit = QLineEdit()
        self.bot_edit.setEnabled(False)
        bot_layout.addWidget(self.bot_edit, 1)
        
        telegram_layout.addLayout(bot_layout)
        
        # Chat ID
        chat_layout = QHBoxLayout()
        chat_label = QLabel("Chat ID:")
        chat_layout.addWidget(chat_label)
        
        self.chat_edit = QLineEdit()
        self.chat_edit.setEnabled(False)
        chat_layout.addWidget(self.chat_edit, 1)
        
        telegram_layout.addLayout(chat_layout)
        
        # Test button
        test_tg_btn = QPushButton("Test Telegram")
        test_tg_btn.clicked.connect(self.test_telegram)
        test_tg_btn.setEnabled(False)
        telegram_layout.addWidget(test_tg_btn)
        
        telegram_group.setLayout(telegram_layout)
        layout.addWidget(telegram_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()

    def setup_cloud_tab(self):
        # Create a scroll area for the cloud services tab
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        
        # Create a widget to hold the content
        content_widget = QWidget()
        
        # Layout for the content
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(15)
        
        # Set the content widget to the scroll area
        scroll_area.setWidget(content_widget)
        
        # Set the scroll area as the main widget for the tab
        tab_layout = QVBoxLayout(self.cloud_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll_area)
        
        # Implement the rest of the cloud services tab content as before
        # Google Drive group
        gdrive_group = QGroupBox("Google Drive")
        gdrive_layout = QVBoxLayout()
        gdrive_layout.setContentsMargins(15, 20, 15, 15)
        gdrive_layout.setSpacing(15)
        
        self.gdrive_check = QCheckBox("Enable Google Drive integration")
        gdrive_layout.addWidget(self.gdrive_check)
        
        self.gdrive_auto_check = QCheckBox("Automatically upload completed downloads")
        gdrive_layout.addWidget(self.gdrive_auto_check)
        
        self.gdrive_folder_check = QCheckBox("Use specific folder")
        gdrive_layout.addWidget(self.gdrive_folder_check)
        
        # Folder selection
        folder_layout = QHBoxLayout()
        folder_label = QLabel("Folder name:")
        folder_layout.addWidget(folder_label)
        
        self.gdrive_folder_edit = QLineEdit()
        folder_layout.addWidget(self.gdrive_folder_edit, 1)
        
        gdrive_layout.addLayout(folder_layout)
        
        # Authenticate button
        auth_btn = QPushButton("Authenticate with Google")
        gdrive_layout.addWidget(auth_btn)
        
        gdrive_group.setLayout(gdrive_layout)
        layout.addWidget(gdrive_group)
        
        # Dropbox group
        dropbox_group = QGroupBox("Dropbox")
        dropbox_layout = QVBoxLayout()
        dropbox_layout.setContentsMargins(15, 20, 15, 15)
        dropbox_layout.setSpacing(15)
        
        self.dropbox_check = QCheckBox("Enable Dropbox integration")
        dropbox_layout.addWidget(self.dropbox_check)
        
        self.dropbox_auto_check = QCheckBox("Automatically upload completed downloads")
        dropbox_layout.addWidget(self.dropbox_auto_check)
        
        self.dropbox_folder_check = QCheckBox("Use specific folder")
        dropbox_layout.addWidget(self.dropbox_folder_check)
        
        # Folder selection
        db_folder_layout = QHBoxLayout()
        db_folder_label = QLabel("Folder path:")
        db_folder_layout.addWidget(db_folder_label)
        
        self.dropbox_folder_edit = QLineEdit()
        db_folder_layout.addWidget(self.dropbox_folder_edit, 1)
        
        dropbox_layout.addLayout(db_folder_layout)
        
        # Authenticate button
        db_auth_btn = QPushButton("Authenticate with Dropbox")
        dropbox_layout.addWidget(db_auth_btn)
        
        dropbox_group.setLayout(dropbox_layout)
        layout.addWidget(dropbox_group)
        
        # OneDrive group
        onedrive_group = QGroupBox("OneDrive")
        onedrive_layout = QVBoxLayout()
        onedrive_layout.setContentsMargins(15, 20, 15, 15)
        onedrive_layout.setSpacing(15)
        
        self.onedrive_check = QCheckBox("Enable OneDrive integration")
        onedrive_layout.addWidget(self.onedrive_check)
        
        self.onedrive_auto_check = QCheckBox("Automatically upload completed downloads")
        onedrive_layout.addWidget(self.onedrive_auto_check)
        
        self.onedrive_folder_check = QCheckBox("Use specific folder")
        onedrive_layout.addWidget(self.onedrive_folder_check)
        
        # Folder selection
        od_folder_layout = QHBoxLayout()
        od_folder_label = QLabel("Folder path:")
        od_folder_layout.addWidget(od_folder_label)
        
        self.onedrive_folder_edit = QLineEdit()
        od_folder_layout.addWidget(self.onedrive_folder_edit, 1)
        
        onedrive_layout.addLayout(od_folder_layout)
        
        # Authenticate button
        od_auth_btn = QPushButton("Authenticate with OneDrive")
        onedrive_layout.addWidget(od_auth_btn)
        
        onedrive_group.setLayout(onedrive_layout)
        layout.addWidget(onedrive_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()

    def browse_download_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Default Download Location")
        if folder:
            self.default_path_edit.setText(folder)
    
    def toggle_bandwidth_limit(self, enabled):
        self.bandwidth_slider.setEnabled(enabled)
    
    def toggle_proxy_settings(self, enabled):
        self.proxy_url_edit.setEnabled(enabled)
        self.proxy_auth_check.setEnabled(enabled)
        
        auth_enabled = enabled and self.proxy_auth_check.isChecked()
        self.proxy_user_edit.setEnabled(auth_enabled)
        self.proxy_pass_edit.setEnabled(auth_enabled)
    
    def toggle_proxy_auth(self, enabled):
        if not self.use_proxy_check.isChecked():
            enabled = False
        
        self.proxy_user_edit.setEnabled(enabled)
        self.proxy_pass_edit.setEnabled(enabled)
    
    def toggle_email_settings(self, enabled):
        self.smtp_edit.setEnabled(enabled)
        self.email_acc_edit.setEnabled(enabled)
        self.email_pass_edit.setEnabled(enabled)
        self.recip_edit.setEnabled(enabled)
    
    def toggle_telegram_settings(self, enabled):
        self.bot_edit.setEnabled(enabled)
        self.chat_edit.setEnabled(enabled)
    
    def test_email(self):
        # In a real implementation, this would test the email settings
        QMessageBox.information(self, "Test Email", "Email settings test functionality will be implemented.")
    
    def test_telegram(self):
        # In a real implementation, this would test the Telegram settings
        QMessageBox.information(self, "Test Telegram", "Telegram settings test functionality will be implemented.")
    
    def loadSettings(self):
        """Load settings from database to UI"""
        # Get all settings
        settings = self.database.get_all_settings()
        
        # General tab
        self.default_path_edit.setText(settings.get('default_save_path', ''))
        self.always_ask_check.setChecked(settings.get('ask_location', False))
        
        # Theme
        theme_text = translations.get_text("dark") if settings.get('theme', 'dark') == 'dark' else translations.get_text("light")
        index = self.theme_combo.findText(theme_text)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
            
        # Language
        lang_code = settings.get('language', translations.current_language)
        lang_index = self.lang_combo.findData(lang_code)
        if lang_index >= 0:
            self.lang_combo.setCurrentIndex(lang_index)
            
        self.tray_check.setChecked(settings.get('minimize_to_tray', False))
        if hasattr(self, 'startup_check'):
            self.startup_check.setChecked(settings.get('autostart', False))
        self.auto_start_check.setChecked(settings.get('auto_start_queue', True))
        self.history_check.setChecked(settings.get('remember_history', True))
        self.shutdown_check.setChecked(settings.get('schedule_shutdown', False))
        
        # Connection tab
        self.default_conn_spin.setValue(settings.get('default_connections', 8))
        self.max_conn_spin.setValue(settings.get('max_connections', 16))
        
        bandwidth_limit = settings.get('bandwidth_limit', 0)
        self.limit_bandwidth_check.setChecked(bandwidth_limit > 0)
        self.bandwidth_slider.setValue(bandwidth_limit if bandwidth_limit > 0 else 200)
        self.toggle_bandwidth_limit(bandwidth_limit > 0)
        
        proxy_enabled = settings.get('proxy_enabled', False)
        self.use_proxy_check.setChecked(proxy_enabled)
        self.proxy_url_edit.setText(settings.get('proxy_url', ''))
        
        proxy_auth = settings.get('proxy_username', '') != ''
        self.proxy_auth_check.setChecked(proxy_auth)
        self.proxy_user_edit.setText(settings.get('proxy_username', ''))
        self.proxy_pass_edit.setText(settings.get('proxy_password', ''))
        
        self.toggle_proxy_settings(proxy_enabled)
        self.toggle_proxy_auth(proxy_auth)
        
        # Notification tab
        self.notify_complete_check.setChecked(settings.get('notifications_enabled', True))
        self.notify_error_check.setChecked(settings.get('sound_enabled', True))
        self.notify_start_check.setChecked(settings.get('notifications_enabled', True))
        
        email_enabled = settings.get('email_notifications', False)
        self.email_check.setChecked(email_enabled)
        self.email_acc_edit.setText(settings.get('email_address', ''))
        self.smtp_edit.setText(settings.get('smtp_server', ''))
        self.email_pass_edit.setText(settings.get('smtp_password', ''))
        self.recip_edit.setText(settings.get('email_address', ''))
        
        self.toggle_email_settings(email_enabled)
        
        telegram_enabled = settings.get('telegram_notifications', False)
        self.telegram_check.setChecked(telegram_enabled)
        self.bot_edit.setText(settings.get('telegram_token', ''))
        self.chat_edit.setText(settings.get('telegram_chat_id', ''))
        
        self.toggle_telegram_settings(telegram_enabled)
        
        # Cloud tab
        self.gdrive_check.setChecked(settings.get('gdrive_enabled', False))
        self.gdrive_auto_check.setChecked(settings.get('gdrive_auto', False))
        self.gdrive_folder_check.setChecked(settings.get('gdrive_folder', False))
        self.gdrive_folder_edit.setText(settings.get('gdrive_folder_name', ''))
        
        self.dropbox_check.setChecked(settings.get('dropbox_enabled', False))
        self.dropbox_auto_check.setChecked(settings.get('dropbox_auto', False))
        self.dropbox_folder_check.setChecked(settings.get('dropbox_folder', False))
        self.dropbox_folder_edit.setText(settings.get('dropbox_folder_path', ''))
        
        self.onedrive_check.setChecked(settings.get('onedrive_enabled', False))
        self.onedrive_auto_check.setChecked(settings.get('onedrive_auto', False))
        self.onedrive_folder_check.setChecked(settings.get('onedrive_folder', False))
        self.onedrive_folder_edit.setText(settings.get('onedrive_folder_path', ''))
    
    def save_settings(self):
        """Save settings from UI to database"""
        # General tab
        self.database.set_setting('default_save_path', self.default_path_edit.text())
        self.database.set_setting('ask_location', self.always_ask_check.isChecked())
        
        # Theme - convert display text back to internal value
        theme = 'dark' if self.theme_combo.currentText() == translations.get_text("dark") else 'light'
        self.database.set_setting('theme', theme)
        
        # Language
        new_lang = self.lang_combo.currentData()
        current_lang = self.database.get_setting('language', translations.current_language)
        
        if new_lang != current_lang:
            self.database.set_setting('language', new_lang)
            # Notify user about language change requiring restart
            QMessageBox.information(self, translations.get_text("app_name"), 
                                    translations.get_text("language_changed"))
        
        self.database.set_setting('minimize_to_tray', self.tray_check.isChecked())
        if hasattr(self, 'startup_check'):
            self.database.set_setting('autostart', self.startup_check.isChecked())
        self.database.set_setting('auto_start_queue', self.auto_start_check.isChecked())
        self.database.set_setting('remember_history', self.history_check.isChecked())
        self.database.set_setting('schedule_shutdown', self.shutdown_check.isChecked())
        
        # Connection tab
        self.database.set_setting('default_connections', self.default_conn_spin.value())
        self.database.set_setting('max_connections', self.max_conn_spin.value())
        
        bandwidth_limit = self.bandwidth_slider.value() if self.limit_bandwidth_check.isChecked() else 0
        self.database.set_setting('bandwidth_limit', bandwidth_limit)
        
        self.database.set_setting('proxy_enabled', self.use_proxy_check.isChecked())
        self.database.set_setting('proxy_url', self.proxy_url_edit.text())
        
        if self.use_proxy_check.isChecked() and self.proxy_auth_check.isChecked():
            self.database.set_setting('proxy_username', self.proxy_user_edit.text())
            self.database.set_setting('proxy_password', self.proxy_pass_edit.text())
        else:
            self.database.set_setting('proxy_username', '')
            self.database.set_setting('proxy_password', '')
        
        # Notification tab
        self.database.set_setting('notifications_enabled', self.notify_complete_check.isChecked())
        self.database.set_setting('sound_enabled', self.notify_error_check.isChecked())
        
        self.database.set_setting('email_notifications', self.email_check.isChecked())
        if self.email_check.isChecked():
            self.database.set_setting('email_address', self.email_acc_edit.text())
            self.database.set_setting('smtp_server', self.smtp_edit.text())
            self.database.set_setting('smtp_password', self.email_pass_edit.text())
        
        self.database.set_setting('telegram_notifications', self.telegram_check.isChecked())
        if self.telegram_check.isChecked():
            self.database.set_setting('telegram_token', self.bot_edit.text())
            self.database.set_setting('telegram_chat_id', self.chat_edit.text())
        
        # Cloud tab
        self.database.set_setting('gdrive_enabled', self.gdrive_check.isChecked())
        self.database.set_setting('gdrive_auto', self.gdrive_auto_check.isChecked())
        self.database.set_setting('gdrive_folder', self.gdrive_folder_check.isChecked())
        self.database.set_setting('gdrive_folder_name', self.gdrive_folder_edit.text())
        
        self.database.set_setting('dropbox_enabled', self.dropbox_check.isChecked())
        self.database.set_setting('dropbox_auto', self.dropbox_auto_check.isChecked())
        self.database.set_setting('dropbox_folder', self.dropbox_folder_check.isChecked())
        self.database.set_setting('dropbox_folder_path', self.dropbox_folder_edit.text())
        
        self.database.set_setting('onedrive_enabled', self.onedrive_check.isChecked())
        self.database.set_setting('onedrive_auto', self.onedrive_auto_check.isChecked())
        self.database.set_setting('onedrive_folder', self.onedrive_folder_check.isChecked())
        self.database.set_setting('onedrive_folder_path', self.onedrive_folder_edit.text())
        
        QMessageBox.information(self, translations.get_text("app_name"), translations.get_text("save"))
        self.accept()

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    dialog = SettingsDialog()
    dialog.exec_() 