import os
import sqlite3
import json
import time
from datetime import datetime

class Database:
    def __init__(self, db_path=None):
        # Set default database path to application directory
        if db_path is None:
            app_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(app_dir, 'adx_downloader.db')
        
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.initialize()
    
    def initialize(self):
        """Initialize the database and create tables if they don't exist"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            # Create downloads history table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    save_path TEXT NOT NULL,
                    file_size INTEGER,
                    status TEXT,
                    start_time INTEGER,
                    end_time INTEGER,
                    connections INTEGER,
                    avg_speed REAL,
                    completed INTEGER DEFAULT 0,
                    metadata TEXT
                )
            ''')
            
            # Create settings table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT
                )
            ''')
            
            # Create scheduled_downloads table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS scheduled_downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    save_path TEXT NOT NULL,
                    schedule_time INTEGER NOT NULL,
                    connections INTEGER,
                    recurring TEXT,
                    status TEXT DEFAULT 'waiting',
                    metadata TEXT
                )
            ''')
            
            # Insert default settings if they don't exist
            default_settings = {
                'default_connections': 8,
                'max_connections': 16,
                'default_save_path': os.path.join(os.path.expanduser("~"), "Downloads"),
                'bandwidth_limit': 0,  # 0 means no limit
                'theme': 'dark',
                'notifications_enabled': 1,
                'sound_enabled': 1,
                'auto_start_queue': 1,
                'proxy_enabled': 0,
                'proxy_url': '',
                'proxy_username': '',
                'proxy_password': '',
                'schedule_shutdown': 0
            }
            
            for key, value in default_settings.items():
                self.cursor.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, json.dumps(value))
                )
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
            return False
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
    
    def add_download(self, url, file_name, save_path, connections=8):
        """Add a new download to history"""
        try:
            current_time = int(time.time())
            self.cursor.execute(
                """INSERT INTO downloads 
                   (url, file_name, save_path, status, start_time, connections) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (url, file_name, save_path, 'started', current_time, connections)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding download: {e}")
            return None
    
    def update_download(self, download_id, **kwargs):
        """Update download information"""
        if not kwargs:
            return False
        
        try:
            set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values())
            values.append(download_id)
            
            self.cursor.execute(
                f"UPDATE downloads SET {set_clause} WHERE id = ?",
                values
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error updating download: {e}")
            return False
    
    def complete_download(self, download_id, file_size, avg_speed):
        """Mark a download as completed"""
        try:
            current_time = int(time.time())
            self.cursor.execute(
                """UPDATE downloads SET 
                   status = ?, end_time = ?, file_size = ?, 
                   avg_speed = ?, completed = 1 
                   WHERE id = ?""",
                ('completed', current_time, file_size, avg_speed, download_id)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error completing download: {e}")
            return False
    
    def get_download_history(self, limit=50, offset=0, order_by="start_time DESC"):
        """Get download history"""
        try:
            self.cursor.execute(
                f"SELECT * FROM downloads ORDER BY {order_by} LIMIT ? OFFSET ?", 
                (limit, offset)
            )
            columns = [description[0] for description in self.cursor.description]
            downloads = []
            
            for row in self.cursor.fetchall():
                download = dict(zip(columns, row))
                downloads.append(download)
            
            return downloads
        except sqlite3.Error as e:
            print(f"Error getting download history: {e}")
            return []
    
    def get_download(self, download_id):
        """Get a specific download by ID"""
        try:
            self.cursor.execute("SELECT * FROM downloads WHERE id = ?", (download_id,))
            columns = [description[0] for description in self.cursor.description]
            row = self.cursor.fetchone()
            
            if row:
                return dict(zip(columns, row))
            return None
        except sqlite3.Error as e:
            print(f"Error getting download: {e}")
            return None
    
    def delete_download(self, download_id):
        """Delete a download from history"""
        try:
            self.cursor.execute("DELETE FROM downloads WHERE id = ?", (download_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error deleting download: {e}")
            return False
    
    def clear_history(self):
        """Clear all download history"""
        try:
            self.cursor.execute("DELETE FROM downloads")
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error clearing history: {e}")
            return False
    
    def get_setting(self, key, default=None):
        """Get a setting value"""
        try:
            self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = self.cursor.fetchone()
            
            if result:
                return json.loads(result[0])
            return default
        except sqlite3.Error as e:
            print(f"Error getting setting: {e}")
            return default
    
    def set_setting(self, key, value):
        """Set a setting value"""
        try:
            serialized_value = json.dumps(value)
            self.cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, serialized_value)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error setting setting: {e}")
            return False
    
    def get_all_settings(self):
        """Get all settings"""
        try:
            self.cursor.execute("SELECT key, value FROM settings")
            settings = {}
            
            for key, value in self.cursor.fetchall():
                settings[key] = json.loads(value)
            
            return settings
        except sqlite3.Error as e:
            print(f"Error getting all settings: {e}")
            return {}
    
    def add_scheduled_download(self, url, save_path, schedule_time, connections=8, recurring=None, metadata=None):
        """Add a scheduled download"""
        try:
            if metadata is not None:
                metadata = json.dumps(metadata)
                
            self.cursor.execute(
                """INSERT INTO scheduled_downloads 
                   (url, save_path, schedule_time, connections, recurring, metadata) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (url, save_path, schedule_time, connections, recurring, metadata)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding scheduled download: {e}")
            return None
    
    def get_scheduled_downloads(self, status='waiting'):
        """Get scheduled downloads with specified status"""
        try:
            if status:
                self.cursor.execute(
                    "SELECT * FROM scheduled_downloads WHERE status = ? ORDER BY schedule_time", 
                    (status,)
                )
            else:
                self.cursor.execute("SELECT * FROM scheduled_downloads ORDER BY schedule_time")
                
            columns = [description[0] for description in self.cursor.description]
            downloads = []
            
            for row in self.cursor.fetchall():
                download = dict(zip(columns, row))
                # Parse metadata if exists
                if download.get('metadata'):
                    download['metadata'] = json.loads(download['metadata'])
                downloads.append(download)
            
            return downloads
        except sqlite3.Error as e:
            print(f"Error getting scheduled downloads: {e}")
            return []
    
    def update_scheduled_download(self, download_id, **kwargs):
        """Update a scheduled download"""
        if not kwargs:
            return False
        
        try:
            # Handle metadata serialization
            if 'metadata' in kwargs and kwargs['metadata'] is not None:
                kwargs['metadata'] = json.dumps(kwargs['metadata'])
                
            set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values())
            values.append(download_id)
            
            self.cursor.execute(
                f"UPDATE scheduled_downloads SET {set_clause} WHERE id = ?",
                values
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error updating scheduled download: {e}")
            return False
    
    def delete_scheduled_download(self, download_id):
        """Delete a scheduled download"""
        try:
            self.cursor.execute("DELETE FROM scheduled_downloads WHERE id = ?", (download_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error deleting scheduled download: {e}")
            return False 