import os
import json
import requests
import webbrowser
import time
from urllib.parse import urlparse, parse_qs, urlencode, quote

class CloudServiceError(Exception):
    """Base exception for cloud service errors"""
    pass

class CloudServiceAuthError(CloudServiceError):
    """Authentication error for cloud services"""
    pass

class CloudService:
    """Base class for cloud service implementations"""
    
    def __init__(self):
        self.authenticated = False
        self.token = None
        self.config_path = None
    
    def authenticate(self):
        """Authenticate with the cloud service"""
        raise NotImplementedError("Authentication not implemented")
    
    def is_authenticated(self):
        """Check if authenticated"""
        return self.authenticated
    
    def logout(self):
        """Logout from the service"""
        self.authenticated = False
        self.token = None
        self.save_config()
    
    def save_config(self):
        """Save configuration to file"""
        if not self.config_path:
            return
            
        config_dir = os.path.dirname(self.config_path)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.get_config(), f)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def load_config(self):
        """Load configuration from file"""
        if not self.config_path or not os.path.exists(self.config_path):
            return False
            
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.set_config(config)
                return True
        except Exception as e:
            print(f"Error loading config: {e}")
            return False
    
    def get_config(self):
        """Get configuration for saving"""
        return {"token": self.token, "authenticated": self.authenticated}
    
    def set_config(self, config):
        """Set configuration from loaded data"""
        self.token = config.get("token")
        self.authenticated = config.get("authenticated", False)
    
    def get_file_info(self, file_url):
        """Get information about a file"""
        raise NotImplementedError("Get file info not implemented")
    
    def get_download_url(self, file_url):
        """Get direct download URL for a file"""
        raise NotImplementedError("Get download URL not implemented")


class GoogleDriveService(CloudService):
    """Implementation for Google Drive"""
    
    def __init__(self, client_id=None, client_secret=None):
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = None
        self.token_expires = 0
        
        # Set up config path
        app_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(app_dir, 'config')
        self.config_path = os.path.join(config_dir, 'gdrive_config.json')
        
        # Try to load existing config
        self.load_config()
    
    def get_config(self):
        """Get configuration for saving"""
        return {
            "token": self.token,
            "refresh_token": self.refresh_token,
            "token_expires": self.token_expires,
            "authenticated": self.authenticated
        }
    
    def set_config(self, config):
        """Set configuration from loaded data"""
        self.token = config.get("token")
        self.refresh_token = config.get("refresh_token")
        self.token_expires = config.get("token_expires", 0)
        self.authenticated = config.get("authenticated", False)
        
        # Check if token is expired and needs refresh
        if self.token and self.refresh_token and time.time() > self.token_expires:
            try:
                self._refresh_access_token()
            except Exception:
                # If refresh fails, we'll need to re-authenticate
                pass
    
    def authenticate(self):
        """Start OAuth flow for Google Drive"""
        if not self.client_id or not self.client_secret:
            raise CloudServiceAuthError("Client ID and Client Secret are required")
        
        # This is a simplification. In a real app, you would:
        # 1. Generate an auth URL
        # 2. Open browser or show URL to user
        # 3. Get the authorization code from redirect
        # 4. Exchange code for tokens
        
        print("Please authenticate with Google in your browser...")
        auth_url = (
            "https://accounts.google.com/o/oauth2/auth?"
            f"client_id={self.client_id}&"
            "response_type=code&"
            "scope=https://www.googleapis.com/auth/drive.readonly&"
            "access_type=offline&"
            "redirect_uri=http://localhost:8080"
        )
        
        webbrowser.open(auth_url)
        
        # In a real app, you would have a local server listening on the redirect URI
        # to capture the authorization code
        auth_code = input("Enter the authorization code from the browser: ")
        
        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": auth_code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": "http://localhost:8080",
            "grant_type": "authorization_code"
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code != 200:
            raise CloudServiceAuthError(f"Authentication failed: {response.text}")
        
        token_data = response.json()
        self.token = token_data.get("access_token")
        self.refresh_token = token_data.get("refresh_token")
        self.token_expires = time.time() + token_data.get("expires_in", 3600)
        self.authenticated = True
        self.save_config()
        
        return True
    
    def _refresh_access_token(self):
        """Refresh the access token using the refresh token"""
        if not self.refresh_token:
            raise CloudServiceAuthError("No refresh token available")
        
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token"
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code != 200:
            raise CloudServiceAuthError(f"Token refresh failed: {response.text}")
        
        token_data = response.json()
        self.token = token_data.get("access_token")
        self.token_expires = time.time() + token_data.get("expires_in", 3600)
        self.save_config()
        
        return True
    
    def get_file_info(self, file_url):
        """Get information about a Google Drive file"""
        # Extract file ID from URL
        file_id = self._extract_file_id(file_url)
        if not file_id:
            raise CloudServiceError("Invalid Google Drive URL")
        
        # Check authentication and refresh if needed
        if not self.is_authenticated() or time.time() > self.token_expires:
            if self.refresh_token:
                self._refresh_access_token()
            else:
                raise CloudServiceAuthError("Not authenticated")
        
        # Get file metadata
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
        params = {"fields": "name,size,mimeType"}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            if response.status_code == 401:
                # Token expired or invalid
                self._refresh_access_token()
                # Retry request
                headers = {"Authorization": f"Bearer {self.token}"}
                response = requests.get(url, headers=headers, params=params)
                if response.status_code != 200:
                    raise CloudServiceError(f"Error getting file info: {response.text}")
            else:
                raise CloudServiceError(f"Error getting file info: {response.text}")
        
        file_info = response.json()
        return {
            "name": file_info.get("name"),
            "size": int(file_info.get("size", 0)),
            "mime_type": file_info.get("mimeType"),
            "url": file_url,
            "file_id": file_id
        }
    
    def get_download_url(self, file_url):
        """Get direct download URL for a Google Drive file"""
        file_id = self._extract_file_id(file_url)
        if not file_id:
            raise CloudServiceError("Invalid Google Drive URL")
        
        # Check authentication and refresh if needed
        if not self.is_authenticated() or time.time() > self.token_expires:
            if self.refresh_token:
                self._refresh_access_token()
            else:
                raise CloudServiceAuthError("Not authenticated")
        
        # Get download URL
        return f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&access_token={self.token}"
    
    def _extract_file_id(self, url):
        """Extract file ID from Google Drive URL"""
        parsed_url = urlparse(url)
        
        # Handle different URL formats
        if parsed_url.netloc == "drive.google.com":
            if parsed_url.path.startswith("/file/d/"):
                # https://drive.google.com/file/d/{file_id}/view
                parts = parsed_url.path.split("/")
                if len(parts) >= 4:
                    return parts[3]
            elif parsed_url.path == "/open":
                # https://drive.google.com/open?id={file_id}
                query = parse_qs(parsed_url.query)
                return query.get("id", [None])[0]
        
        return None


class DropboxService(CloudService):
    """Implementation for Dropbox"""
    
    def __init__(self, app_key=None, app_secret=None):
        super().__init__()
        self.app_key = app_key
        self.app_secret = app_secret
        
        # Set up config path
        app_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(app_dir, 'config')
        self.config_path = os.path.join(config_dir, 'dropbox_config.json')
        
        # Try to load existing config
        self.load_config()
    
    def authenticate(self):
        """Start OAuth flow for Dropbox"""
        if not self.app_key or not self.app_secret:
            raise CloudServiceAuthError("App Key and App Secret are required")
        
        # This is a simplification. In a real app, you would:
        # 1. Generate an auth URL
        # 2. Open browser or show URL to user
        # 3. Get the authorization code from redirect
        # 4. Exchange code for tokens
        
        print("Please authenticate with Dropbox in your browser...")
        auth_url = (
            "https://www.dropbox.com/oauth2/authorize?"
            f"client_id={self.app_key}&"
            "response_type=code&"
            "token_access_type=offline"
        )
        
        webbrowser.open(auth_url)
        
        # In a real app, you would have a local server listening on the redirect URI
        # to capture the authorization code
        auth_code = input("Enter the authorization code from the browser: ")
        
        # Exchange code for tokens
        token_url = "https://api.dropboxapi.com/oauth2/token"
        data = {
            "code": auth_code,
            "grant_type": "authorization_code",
            "client_id": self.app_key,
            "client_secret": self.app_secret
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code != 200:
            raise CloudServiceAuthError(f"Authentication failed: {response.text}")
        
        token_data = response.json()
        self.token = token_data.get("access_token")
        self.authenticated = True
        self.save_config()
        
        return True
    
    def get_file_info(self, file_url):
        """Get information about a Dropbox file"""
        # Extract file path from URL
        file_path = self._extract_file_path(file_url)
        if not file_path:
            raise CloudServiceError("Invalid Dropbox URL")
        
        # Check authentication
        if not self.is_authenticated():
            raise CloudServiceAuthError("Not authenticated")
        
        # Get file metadata
        url = "https://api.dropboxapi.com/2/files/get_metadata"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        data = {"path": file_path}
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            raise CloudServiceError(f"Error getting file info: {response.text}")
        
        file_info = response.json()
        return {
            "name": file_info.get("name"),
            "size": file_info.get("size", 0),
            "path": file_path,
            "url": file_url
        }
    
    def get_download_url(self, file_url):
        """Get direct download URL for a Dropbox file"""
        file_path = self._extract_file_path(file_url)
        if not file_path:
            raise CloudServiceError("Invalid Dropbox URL")
        
        # Check authentication
        if not self.is_authenticated():
            raise CloudServiceAuthError("Not authenticated")
        
        # Create direct download link
        url = "https://api.dropboxapi.com/2/files/get_temporary_link"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        data = {"path": file_path}
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            raise CloudServiceError(f"Error getting download URL: {response.text}")
        
        link_data = response.json()
        return link_data.get("link")
    
    def _extract_file_path(self, url):
        """Extract file path from Dropbox URL"""
        parsed_url = urlparse(url)
        
        # Handle different URL formats
        if parsed_url.netloc in ["www.dropbox.com", "dropbox.com"]:
            if parsed_url.path.startswith("/s/"):
                # Shared link - we need to resolve it
                # This is simplified - in a real app, you would use the Dropbox API
                return None
            elif parsed_url.path.startswith("/scl/"):
                # Another shared link format
                return None
            else:
                # Handle direct path format
                return parsed_url.path
        
        return None


class OneDriveService(CloudService):
    """Implementation for OneDrive"""
    
    def __init__(self, client_id=None, client_secret=None):
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = None
        self.token_expires = 0
        
        # Set up config path
        app_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(app_dir, 'config')
        self.config_path = os.path.join(config_dir, 'onedrive_config.json')
        
        # Try to load existing config
        self.load_config()
    
    def get_config(self):
        """Get configuration for saving"""
        return {
            "token": self.token,
            "refresh_token": self.refresh_token,
            "token_expires": self.token_expires,
            "authenticated": self.authenticated
        }
    
    def set_config(self, config):
        """Set configuration from loaded data"""
        self.token = config.get("token")
        self.refresh_token = config.get("refresh_token")
        self.token_expires = config.get("token_expires", 0)
        self.authenticated = config.get("authenticated", False)
        
        # Check if token is expired and needs refresh
        if self.token and self.refresh_token and time.time() > self.token_expires:
            try:
                self._refresh_access_token()
            except Exception:
                # If refresh fails, we'll need to re-authenticate
                pass
    
    def authenticate(self):
        """Start OAuth flow for OneDrive"""
        if not self.client_id or not self.client_secret:
            raise CloudServiceAuthError("Client ID and Client Secret are required")
        
        # This is a simplification. In a real app, you would:
        # 1. Generate an auth URL
        # 2. Open browser or show URL to user
        # 3. Get the authorization code from redirect
        # 4. Exchange code for tokens
        
        print("Please authenticate with OneDrive in your browser...")
        auth_url = (
            "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
            f"client_id={self.client_id}&"
            "response_type=code&"
            "scope=files.read offline_access&"
            "redirect_uri=http://localhost:8080"
        )
        
        webbrowser.open(auth_url)
        
        # In a real app, you would have a local server listening on the redirect URI
        # to capture the authorization code
        auth_code = input("Enter the authorization code from the browser: ")
        
        # Exchange code for tokens
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        data = {
            "code": auth_code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": "http://localhost:8080",
            "grant_type": "authorization_code"
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code != 200:
            raise CloudServiceAuthError(f"Authentication failed: {response.text}")
        
        token_data = response.json()
        self.token = token_data.get("access_token")
        self.refresh_token = token_data.get("refresh_token")
        self.token_expires = time.time() + token_data.get("expires_in", 3600)
        self.authenticated = True
        self.save_config()
        
        return True
    
    def _refresh_access_token(self):
        """Refresh the access token using the refresh token"""
        if not self.refresh_token:
            raise CloudServiceAuthError("No refresh token available")
        
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        data = {
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token"
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code != 200:
            raise CloudServiceAuthError(f"Token refresh failed: {response.text}")
        
        token_data = response.json()
        self.token = token_data.get("access_token")
        self.token_expires = time.time() + token_data.get("expires_in", 3600)
        self.save_config()
        
        return True
    
    def get_file_info(self, file_url):
        """Get information about a OneDrive file"""
        # Extract item ID and drive ID from URL
        file_id = self._extract_file_id(file_url)
        if not file_id:
            raise CloudServiceError("Invalid OneDrive URL")
        
        # Check authentication and refresh if needed
        if not self.is_authenticated() or time.time() > self.token_expires:
            if self.refresh_token:
                self._refresh_access_token()
            else:
                raise CloudServiceAuthError("Not authenticated")
        
        # Get file metadata
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            if response.status_code == 401:
                # Token expired or invalid
                self._refresh_access_token()
                # Retry request
                headers = {"Authorization": f"Bearer {self.token}"}
                response = requests.get(url, headers=headers)
                if response.status_code != 200:
                    raise CloudServiceError(f"Error getting file info: {response.text}")
            else:
                raise CloudServiceError(f"Error getting file info: {response.text}")
        
        file_info = response.json()
        return {
            "name": file_info.get("name"),
            "size": file_info.get("size", 0),
            "url": file_url,
            "file_id": file_id
        }
    
    def get_download_url(self, file_url):
        """Get direct download URL for a OneDrive file"""
        file_id = self._extract_file_id(file_url)
        if not file_id:
            raise CloudServiceError("Invalid OneDrive URL")
        
        # Check authentication and refresh if needed
        if not self.is_authenticated() or time.time() > self.token_expires:
            if self.refresh_token:
                self._refresh_access_token()
            else:
                raise CloudServiceAuthError("Not authenticated")
        
        # Get download URL
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.get(url, headers=headers, allow_redirects=False)
        if response.status_code == 302:
            # Follow redirect to get the download URL
            return response.headers.get("Location")
        else:
            raise CloudServiceError(f"Error getting download URL: {response.status_code} - {response.text}")
    
    def _extract_file_id(self, url):
        """Extract file ID from OneDrive URL"""
        parsed_url = urlparse(url)
        
        # Handle different URL formats
        if parsed_url.netloc in ["onedrive.live.com", "1drv.ms"]:
            query = parse_qs(parsed_url.query)
            
            # Look for item ID in query parameters
            if "id" in query:
                return query["id"][0]
            elif "resid" in query:
                return query["resid"][0]
        
        return None


# Factory to create cloud service instances
def create_cloud_service(service_name, **kwargs):
    """Create a cloud service instance by name"""
    if service_name.lower() == "gdrive" or service_name.lower() == "google_drive":
        return GoogleDriveService(**kwargs)
    elif service_name.lower() == "dropbox":
        return DropboxService(**kwargs)
    elif service_name.lower() == "onedrive":
        return OneDriveService(**kwargs)
    else:
        raise ValueError(f"Unsupported cloud service: {service_name}")


def detect_cloud_service(url):
    """Detect cloud service from URL"""
    parsed_url = urlparse(url)
    
    if parsed_url.netloc in ["drive.google.com", "docs.google.com"]:
        return "gdrive"
    elif parsed_url.netloc in ["dropbox.com", "www.dropbox.com"]:
        return "dropbox"
    elif parsed_url.netloc in ["onedrive.live.com", "1drv.ms"]:
        return "onedrive"
    else:
        return None 