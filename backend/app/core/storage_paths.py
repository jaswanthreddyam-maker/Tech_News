import re
from pathlib import Path
from app.core.config import settings

class StoragePathService:
    @staticmethod
    def clean_relative(path: str | None) -> str | None:
        """
        Extracts the relative path (e.g. 'thumbnails/hash.webp') from any filesystem path,
        public URL, or historical prefix format.
        """
        if not path:
            return None
            
        # Standalone check for general UI fallback/static images
        if path.startswith("/images/") or path.startswith("images/"):
            # Normalize to include leading slash for client assets
            return f"/{path.lstrip('/')}"
            
        # Standardize separators to forward slashes and strip leading/trailing slashes
        path_str = path.replace("\\", "/").strip("/")
        
        # Build list of historical and configured prefixes to strip
        prefixes = [
            "app/storage/uploads/",
            "app/uploads/",
            "runtime/storage/uploads/",
            "runtime/uploads/",
            "api/v1/uploads/",
            "uploads/",
            "./uploads/",
        ]
        
        # Dynamically append configured prefixes from settings to handle local overrides
        storage_root_clean = settings.STORAGE_ROOT.replace('\\', '/')
        dynamic_prefixes = [
            settings.UPLOAD_DIR.replace("\\", "/"),
            f"{storage_root_clean}/uploads",
            settings.UPLOAD_PUBLIC_PREFIX.replace("\\", "/"),
        ]
        for dp in dynamic_prefixes:
            dp_clean = dp.strip("/") + "/"
            if dp_clean not in prefixes:
                prefixes.append(dp_clean)
                
        # Sort prefixes by length descending to prevent partial prefix matching issues
        prefixes.sort(key=len, reverse=True)
        
        # Strip the matching prefix
        for prefix in prefixes:
            if path_str.startswith(prefix):
                path_str = path_str[len(prefix):]
                break
                
        return path_str

    @staticmethod
    def to_public_url(relative_path: str | None) -> str | None:
        """
        Converts a relative path to its serving public URL using UPLOAD_PUBLIC_PREFIX.
        """
        if not relative_path:
            return None
        if relative_path.startswith("/images/"):
            return relative_path
        public_prefix = settings.UPLOAD_PUBLIC_PREFIX.rstrip("/")
        return f"{public_prefix}/{relative_path.lstrip('/')}"

    @staticmethod
    def to_filesystem_path(relative_path: str | None) -> str | None:
        """
        Converts a relative path to a local absolute filesystem path inside the container.
        """
        if not relative_path:
            return None
        if relative_path.startswith("/images/"):
            return None  # Fallback assets are hosted publicly by the frontend
        return str(Path(settings.UPLOAD_DIR) / relative_path.lstrip("/"))

    @staticmethod
    def from_public_url(public_url: str | None) -> str | None:
        """
        Converts a public URL back to a clean relative path.
        """
        return StoragePathService.clean_relative(public_url)
