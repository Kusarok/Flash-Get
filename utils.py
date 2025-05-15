import os
import sys
import hashlib
import time
import tempfile
import subprocess
import socket
import platform
import shutil
from pathlib import Path
import threading
import webbrowser
import mimetypes
from urllib.parse import urlparse
import ctypes
from PyQt5.QtCore import QStandardPaths

# Define constants
APP_NAME = "ADX Downloader"
APP_VERSION = "1.0.0"
USER_AGENT = f"{APP_NAME}/{APP_VERSION}"

def get_app_data_dir():
    """Get application data directory"""
    app_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    if not app_dir:
        # Fallback
        app_dir = os.path.join(os.path.expanduser("~"), ".adxdownloader")
    
    # Create directory if it doesn't exist
    if not os.path.exists(app_dir):
        os.makedirs(app_dir)
    
    return app_dir

def get_app_config_dir():
    """Get application configuration directory"""
    config_dir = os.path.join(get_app_data_dir(), "config")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    return config_dir

def get_downloads_dir():
    """Get default downloads directory"""
    return QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)

def is_valid_url(url):
    """Check if URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def get_filename_from_url(url):
    """Extract filename from URL"""
    parsed_url = urlparse(url)
    path = parsed_url.path
    
    # Get basename from path
    filename = os.path.basename(path)
    
    # If filename is empty or doesn't have an extension, use a default name
    if not filename or '.' not in filename:
        return "download"
    
    return filename

def get_file_extension(filename):
    """Get file extension from filename"""
    _, ext = os.path.splitext(filename)
    return ext.lower()

def format_size(size_bytes):
    """Format size in bytes to human-readable string"""
    if size_bytes < 1024:
        return f"{size_bytes:.2f} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.2f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.2f} GB"

def parse_size(size_str):
    """Parse size string to bytes"""
    size_str = size_str.strip().upper()
    units = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 * 1024,
        "GB": 1024 * 1024 * 1024,
        "TB": 1024 * 1024 * 1024 * 1024
    }
    
    try:
        number = ""
        unit = ""
        
        for char in size_str:
            if char.isdigit() or char == '.':
                number += char
            else:
                unit += char
        
        number = float(number)
        unit = unit.strip()
        
        if unit in units:
            return int(number * units[unit])
        else:
            return int(number)
    except:
        return 0

def format_time(seconds):
    """Format seconds to human-readable time string"""
    if seconds < 60:
        return f"{seconds:.0f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.0f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"

def format_time_detailed(seconds):
    """Format seconds to detailed time string (HH:MM:SS)"""
    if seconds < 0:
        return "--:--:--"
    
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def get_file_hash(file_path, hash_type="md5", block_size=65536):
    """Calculate file hash"""
    if not os.path.exists(file_path):
        return None
    
    if hash_type == "md5":
        hasher = hashlib.md5()
    elif hash_type == "sha1":
        hasher = hashlib.sha1()
    elif hash_type == "sha256":
        hasher = hashlib.sha256()
    else:
        return None
    
    with open(file_path, 'rb') as f:
        buf = f.read(block_size)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(block_size)
    
    return hasher.hexdigest()

def get_file_mime_type(file_path):
    """Get file MIME type"""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"

def open_file(file_path):
    """Open a file with the default application"""
    if platform.system() == 'Windows':
        os.startfile(file_path)
    elif platform.system() == 'Darwin':  # macOS
        subprocess.call(['open', file_path])
    else:  # Linux and others
        subprocess.call(['xdg-open', file_path])

def open_directory(dir_path):
    """Open directory in file explorer"""
    if platform.system() == 'Windows':
        os.startfile(dir_path)
    elif platform.system() == 'Darwin':  # macOS
        subprocess.call(['open', dir_path])
    else:  # Linux and others
        subprocess.call(['xdg-open', dir_path])

def show_in_explorer(file_path):
    """Show file in explorer/finder with selection"""
    if platform.system() == 'Windows':
        subprocess.run(['explorer', '/select,', file_path])
    elif platform.system() == 'Darwin':  # macOS
        subprocess.call(['open', '-R', file_path])
    else:  # Linux
        directory = os.path.dirname(file_path)
        subprocess.call(['xdg-open', directory])

def check_free_space(path):
    """Check free space in directory"""
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value
    else:
        st = os.statvfs(path)
        return st.f_bavail * st.f_frsize

def is_port_in_use(port):
    """Check if port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_free_port(start_port=8000, max_port=9000):
    """Find a free port in range"""
    for port in range(start_port, max_port):
        if not is_port_in_use(port):
            return port
    return None

def is_process_running(process_name):
    """Check if a process is running by name"""
    if platform.system() == 'Windows':
        output = subprocess.check_output(['tasklist']).decode()
        return process_name.lower() in output.lower()
    else:
        output = subprocess.check_output(['ps', '-A']).decode()
        return process_name.lower() in output.lower()

def is_internet_connected(test_url="https://www.google.com", timeout=5):
    """Check if internet is connected"""
    try:
        import urllib.request
        urllib.request.urlopen(test_url, timeout=timeout)
        return True
    except:
        return False

def get_system_proxy():
    """Get system proxy settings"""
    proxies = {}
    
    if platform.system() == 'Windows':
        try:
            import winreg
            reg_key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            )
            proxy_enabled = winreg.QueryValueEx(reg_key, "ProxyEnable")[0]
            
            if proxy_enabled:
                proxy_server = winreg.QueryValueEx(reg_key, "ProxyServer")[0]
                proxies["http"] = f"http://{proxy_server}"
                proxies["https"] = f"http://{proxy_server}"
        except:
            pass
    
    return proxies

def shutdown_computer(delay=60):
    """Shut down the computer after delay (in seconds)"""
    if platform.system() == 'Windows':
        os.system(f'shutdown /s /t {delay}')
    else:
        os.system(f'shutdown -h +{delay//60}')

def cancel_shutdown():
    """Cancel scheduled shutdown"""
    if platform.system() == 'Windows':
        os.system('shutdown /a')
    else:
        os.system('shutdown -c')

def get_system_temp_dir():
    """Get system temporary directory"""
    return tempfile.gettempdir()

def create_temp_file(suffix=None):
    """Create a temporary file and return its path"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_file.close()
    return temp_file.name

def create_temp_dir():
    """Create a temporary directory and return its path"""
    return tempfile.mkdtemp()

def get_available_browsers():
    """Get list of available browsers on the system"""
    browsers = []
    
    # Check common browsers
    common_browsers = {
        'windows': [
            ('chrome', r'C:\Program Files\Google\Chrome\Application\chrome.exe'),
            ('chrome', r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'),
            ('firefox', r'C:\Program Files\Mozilla Firefox\firefox.exe'),
            ('firefox', r'C:\Program Files (x86)\Mozilla Firefox\firefox.exe'),
            ('edge', r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'),
            ('edge', r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'),
        ],
        'darwin': [
            ('chrome', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
            ('firefox', '/Applications/Firefox.app/Contents/MacOS/firefox'),
            ('safari', '/Applications/Safari.app/Contents/MacOS/Safari'),
        ],
        'linux': [
            ('chrome', '/usr/bin/google-chrome'),
            ('chrome', '/usr/bin/google-chrome-stable'),
            ('firefox', '/usr/bin/firefox'),
            ('chromium', '/usr/bin/chromium'),
            ('chromium', '/usr/bin/chromium-browser'),
        ]
    }
    
    system = platform.system().lower()
    if system == 'windows':
        check_paths = common_browsers['windows']
    elif system == 'darwin':
        check_paths = common_browsers['darwin']
    else:
        check_paths = common_browsers['linux']
    
    for browser_name, path in check_paths:
        if os.path.exists(path):
            browsers.append((browser_name, path))
    
    return browsers

def open_browser(url, browser=None):
    """Open URL in specified browser or default browser"""
    if browser:
        try:
            webbrowser.get(browser).open(url)
            return True
        except:
            pass
    
    # Use default browser as fallback
    return webbrowser.open(url)

def make_portable_dir(install_dir):
    """Create directories for portable mode"""
    os.makedirs(os.path.join(install_dir, 'config'), exist_ok=True)
    os.makedirs(os.path.join(install_dir, 'data'), exist_ok=True)
    os.makedirs(os.path.join(install_dir, 'downloads'), exist_ok=True)
    return True

def is_portable_mode(app_path):
    """Check if application is running in portable mode"""
    app_dir = os.path.dirname(os.path.abspath(app_path))
    config_dir = os.path.join(app_dir, 'config')
    return os.path.exists(config_dir)

def get_network_interfaces():
    """Get list of network interfaces"""
    interfaces = []
    
    if platform.system() == 'Windows':
        # Use ipconfig on Windows
        try:
            output = subprocess.check_output(['ipconfig', '/all']).decode('latin1')
            # Parse the output to extract interface information
            # (simplified implementation)
            interfaces = [line.strip() for line in output.split('\n') 
                         if 'adapter' in line.lower() and ':' in line]
        except:
            pass
    else:
        # Use ifconfig on Unix-like systems
        try:
            output = subprocess.check_output(['ifconfig']).decode('utf-8')
            # Parse the output to extract interface information
            # (simplified implementation)
            interfaces = [line.strip() for line in output.split('\n') 
                         if line and not line.startswith(' ')]
        except:
            pass
    
    return interfaces

def get_file_icon(file_path):
    """Get file icon (system dependent, returns path to icon file)"""
    # This is a stub implementation
    # In a real app, you would use system-specific methods to get file icons
    ext = get_file_extension(file_path)
    
    # Return a default icon path based on extension
    return f"icons/{ext[1:]}.png"  # Assuming icons are in an 'icons' directory 