import os
import time
import platform
import threading
import subprocess
import tempfile
import json
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon

# Attempt to import platform-specific notification libraries
try:
    if platform.system() == 'Windows':
        from win10toast import ToastNotifier
    elif platform.system() == 'Darwin':  # macOS
        import objc
        import Foundation
        import AppKit
    else:  # Linux
        import dbus
except ImportError:
    pass  # We'll handle fallbacks later

class Notification:
    """Simple notification data class"""
    def __init__(self, title, message, icon=None, timeout=5, actions=None):
        self.title = title
        self.message = message
        self.icon = icon
        self.timeout = timeout  # in seconds
        self.actions = actions or []  # List of (action_name, callback) tuples
        self.timestamp = time.time()
        self.id = f"notification_{int(self.timestamp)}_{id(self)}"

class NotificationAction:
    """Action that can be attached to a notification"""
    def __init__(self, name, callback):
        self.name = name
        self.callback = callback

class NotificationSignals(QObject):
    """Qt signals for notification events"""
    notification_clicked = pyqtSignal(str)  # notification_id
    notification_action = pyqtSignal(str, str)  # notification_id, action_name
    notification_closed = pyqtSignal(str)  # notification_id

class NotificationSystem:
    """Cross-platform notification system"""
    
    def __init__(self, app_name="ADX Downloader", app_icon=None):
        self.app_name = app_name
        self.app_icon = app_icon
        self.signals = NotificationSignals()
        self.active_notifications = {}
        self.system = platform.system()
        self.enabled = True
        self.sound_enabled = True
        
        # Initialize platform-specific notification systems
        self._init_notification_system()
    
    def _init_notification_system(self):
        """Initialize the appropriate notification system for the platform"""
        if self.system == 'Windows':
            self._init_windows_notifications()
        elif self.system == 'Darwin':  # macOS
            self._init_macos_notifications()
        else:  # Linux and others
            self._init_linux_notifications()
    
    def _init_windows_notifications(self):
        """Initialize Windows notification system"""
        try:
            self.win_notifier = ToastNotifier()
            self.has_native = True
        except (ImportError, NameError):
            self.has_native = False
    
    def _init_macos_notifications(self):
        """Initialize macOS notification system"""
        try:
            self.has_native = True
        except (ImportError, NameError):
            self.has_native = False
    
    def _init_linux_notifications(self):
        """Initialize Linux notification system"""
        try:
            self.session_bus = dbus.SessionBus()
            self.notify_interface = dbus.Interface(
                self.session_bus.get_object(
                    'org.freedesktop.Notifications',
                    '/org/freedesktop/Notifications'
                ),
                'org.freedesktop.Notifications'
            )
            self.has_native = True
        except (ImportError, NameError, Exception):
            self.has_native = False
    
    def set_enabled(self, enabled):
        """Enable or disable notifications"""
        self.enabled = enabled
    
    def set_sound_enabled(self, enabled):
        """Enable or disable notification sounds"""
        self.sound_enabled = enabled
    
    def notify(self, title, message, icon=None, timeout=5, actions=None):
        """Send a notification"""
        if not self.enabled:
            return None
        
        notification = Notification(title, message, icon, timeout, actions)
        self.active_notifications[notification.id] = notification
        
        if self.has_native:
            self._send_native_notification(notification)
        else:
            self._send_fallback_notification(notification)
        
        if self.sound_enabled:
            self._play_notification_sound()
        
        return notification.id
    
    def _send_native_notification(self, notification):
        """Send notification using native APIs"""
        if self.system == 'Windows':
            self._send_windows_notification(notification)
        elif self.system == 'Darwin':
            self._send_macos_notification(notification)
        else:
            self._send_linux_notification(notification)
    
    def _send_windows_notification(self, notification):
        """Send Windows toast notification"""
        icon_path = notification.icon or self.app_icon
        
        try:
            # Windows 10 Toast Notifications
            self.win_notifier.show_toast(
                title=notification.title,
                msg=notification.message,
                icon_path=icon_path,
                duration=notification.timeout,
                threaded=True
            )
        except Exception as e:
            print(f"Error sending Windows notification: {e}")
            self._send_fallback_notification(notification)
    
    def _send_macos_notification(self, notification):
        """Send macOS notification center notification"""
        try:
            # Create and deliver notification using NSUserNotification
            NSUserNotification = objc.lookUpClass('NSUserNotification')
            NSUserNotificationCenter = objc.lookUpClass('NSUserNotificationCenter')
            
            notification_obj = NSUserNotification.alloc().init()
            notification_obj.setTitle_(notification.title)
            notification_obj.setInformativeText_(notification.message)
            
            # Set the notification timeout
            notification_obj.setDeliveryDate_(Foundation.NSDate.dateWithTimeInterval_sinceDate_(
                notification.timeout, Foundation.NSDate.date()
            ))
            
            # Deliver notification
            NSUserNotificationCenter.defaultUserNotificationCenter().scheduleNotification_(notification_obj)
        except Exception as e:
            print(f"Error sending macOS notification: {e}")
            self._send_fallback_notification(notification)
    
    def _send_linux_notification(self, notification):
        """Send Linux notification"""
        try:
            # Use DBus to send notification
            icon = notification.icon or ''
            actions_list = []
            hints = {}
            
            for action in notification.actions:
                actions_list.extend([action.name, action.name])
            
            self.notify_interface.Notify(
                self.app_name,  # App name
                0,              # ID (0 = create new)
                icon,           # Icon path
                notification.title,  # Title
                notification.message,  # Body
                actions_list,   # Actions
                hints,          # Hints
                notification.timeout * 1000  # Timeout in ms
            )
        except Exception as e:
            print(f"Error sending Linux notification: {e}")
            self._send_fallback_notification(notification)
    
    def _send_fallback_notification(self, notification):
        """Send fallback notification using Qt system tray"""
        if not hasattr(self, 'tray_icon'):
            # We'll handle this case where Qt isn't fully initialized
            print(f"Notification (fallback): {notification.title} - {notification.message}")
            return
        
        icon = QIcon(notification.icon) if notification.icon else QIcon()
        self.tray_icon.showMessage(
            notification.title,
            notification.message,
            icon,
            notification.timeout * 1000
        )
    
    def _play_notification_sound(self):
        """Play a notification sound"""
        if not self.sound_enabled:
            return
        
        sound_file = os.path.join(os.path.dirname(__file__), 'sounds', 'notification.wav')
        
        if not os.path.exists(sound_file):
            return
        
        try:
            if self.system == 'Windows':
                import winsound
                winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                # Use subprocess to play sound on other platforms
                if self.system == 'Darwin':  # macOS
                    subprocess.Popen(['afplay', sound_file])
                else:  # Linux
                    subprocess.Popen(['aplay', sound_file])
        except Exception as e:
            print(f"Error playing notification sound: {e}")
    
    def setup_tray_icon(self, tray_icon):
        """Set up system tray icon for fallback notifications"""
        self.tray_icon = tray_icon
        
        # Connect tray icon signals
        self.tray_icon.messageClicked.connect(self._handle_tray_notification_clicked)
    
    def _handle_tray_notification_clicked(self):
        """Handle click on tray notification"""
        # Find the most recent notification
        if not self.active_notifications:
            return
        
        # Get most recent notification
        latest_notification = max(
            self.active_notifications.values(),
            key=lambda n: n.timestamp
        )
        
        self.signals.notification_clicked.emit(latest_notification.id)
    
    def clear_notifications(self):
        """Clear all active notifications"""
        self.active_notifications.clear()
    
    def remove_notification(self, notification_id):
        """Remove a notification from active list"""
        if notification_id in self.active_notifications:
            del self.active_notifications[notification_id]


class EmailNotifier:
    """Send notifications via email"""
    
    def __init__(self, smtp_server, smtp_port, username, password, use_tls=True):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.enabled = False
    
    def set_enabled(self, enabled):
        """Enable or disable email notifications"""
        self.enabled = enabled
    
    def send_notification(self, to_email, subject, message):
        """Send email notification"""
        if not self.enabled:
            return False
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()
            
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            print(f"Error sending email notification: {e}")
            return False


class TelegramNotifier:
    """Send notifications via Telegram"""
    
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = False
    
    def set_enabled(self, enabled):
        """Enable or disable Telegram notifications"""
        self.enabled = enabled
    
    def send_notification(self, message):
        """Send Telegram notification"""
        if not self.enabled:
            return False
        
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, data=data)
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending Telegram notification: {e}")
            return False


class NotificationManager:
    """Manage multiple notification channels"""
    
    def __init__(self, app_name="ADX Downloader", app_icon=None):
        self.app_name = app_name
        self.app_icon = app_icon
        self.system_notifier = NotificationSystem(app_name, app_icon)
        self.email_notifier = None
        self.telegram_notifier = None
        
        # Notification queue for rate limiting
        self.notification_queue = []
        self.queue_lock = threading.Lock()
        self.queue_processing = False
    
    def setup_email_notifier(self, smtp_server, smtp_port, username, password, use_tls=True):
        """Set up email notifier"""
        self.email_notifier = EmailNotifier(smtp_server, smtp_port, username, password, use_tls)
    
    def setup_telegram_notifier(self, bot_token, chat_id):
        """Set up Telegram notifier"""
        self.telegram_notifier = TelegramNotifier(bot_token, chat_id)
    
    def enable_email_notifications(self, enabled, to_email=None):
        """Enable or disable email notifications"""
        if self.email_notifier:
            self.email_notifier.set_enabled(enabled)
            self.email_notifier.to_email = to_email
    
    def enable_telegram_notifications(self, enabled):
        """Enable or disable Telegram notifications"""
        if self.telegram_notifier:
            self.telegram_notifier.set_enabled(enabled)
    
    def enable_system_notifications(self, enabled):
        """Enable or disable system notifications"""
        self.system_notifier.set_enabled(enabled)
    
    def enable_notification_sounds(self, enabled):
        """Enable or disable notification sounds"""
        self.system_notifier.set_sound_enabled(enabled)
    
    def notify(self, title, message, channels=None, icon=None, timeout=5, actions=None):
        """Send notification to specified channels"""
        notification_id = None
        channels = channels or ['system']
        
        # Add to notification queue
        with self.queue_lock:
            self.notification_queue.append({
                'title': title,
                'message': message,
                'channels': channels,
                'icon': icon,
                'timeout': timeout,
                'actions': actions,
                'timestamp': time.time()
            })
            
            if not self.queue_processing:
                self.queue_processing = True
                threading.Thread(target=self._process_notification_queue, daemon=True).start()
        
        # Always send system notification immediately
        if 'system' in channels:
            notification_id = self.system_notifier.notify(
                title, message, icon, timeout, actions
            )
        
        return notification_id
    
    def _process_notification_queue(self):
        """Process notification queue with rate limiting"""
        while True:
            with self.queue_lock:
                if not self.notification_queue:
                    self.queue_processing = False
                    break
                
                notification = self.notification_queue.pop(0)
            
            # Process other channels with rate limiting
            channels = notification['channels']
            
            if 'email' in channels and self.email_notifier and self.email_notifier.enabled:
                if hasattr(self.email_notifier, 'to_email') and self.email_notifier.to_email:
                    self.email_notifier.send_notification(
                        self.email_notifier.to_email,
                        notification['title'],
                        notification['message']
                    )
            
            if 'telegram' in channels and self.telegram_notifier and self.telegram_notifier.enabled:
                self.telegram_notifier.send_notification(
                    f"*{notification['title']}*\n{notification['message']}"
                )
            
            # Rate limiting delay
            time.sleep(1)
    
    def setup_tray_icon(self, tray_icon):
        """Set up system tray icon for notifications"""
        self.system_notifier.setup_tray_icon(tray_icon)
    
    def get_signals(self):
        """Get notification signals"""
        return self.system_notifier.signals 