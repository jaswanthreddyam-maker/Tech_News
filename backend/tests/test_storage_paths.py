from pathlib import Path
from app.core.config import settings
from app.core.storage_paths import StoragePathService

def test_clean_relative():
    # Absolute and local container paths
    assert StoragePathService.clean_relative("/app/uploads/thumbnails/a.webp") == "thumbnails/a.webp"
    assert StoragePathService.clean_relative("/app/storage/uploads/thumbnails/b.webp") == "thumbnails/b.webp"
    
    # Host runtime paths
    assert StoragePathService.clean_relative("runtime/storage/uploads/thumbnails/c.webp") == "thumbnails/c.webp"
    assert StoragePathService.clean_relative("runtime/uploads/thumbnails/d.webp") == "thumbnails/d.webp"
    
    # Relative formats
    assert StoragePathService.clean_relative("uploads/thumbnails/e.webp") == "thumbnails/e.webp"
    assert StoragePathService.clean_relative("./uploads/thumbnails/f.webp") == "thumbnails/f.webp"
    
    # Public URLs
    assert StoragePathService.clean_relative("/api/v1/uploads/thumbnails/g.webp") == "thumbnails/g.webp"
    assert StoragePathService.clean_relative("api/v1/uploads/thumbnails/h.webp") == "thumbnails/h.webp"
    
    # Already clean path
    assert StoragePathService.clean_relative("thumbnails/i.webp") == "thumbnails/i.webp"
    
    # Fallback and public assets
    assert StoragePathService.clean_relative("/images/fallback-news.webp") == "/images/fallback-news.webp"
    assert StoragePathService.clean_relative("images/fallback-news.webp") == "/images/fallback-news.webp"
    
    # External URLs
    assert StoragePathService.clean_relative("http://nvidia.com/blog/card.jpg") == "http://nvidia.com/blog/card.jpg"
    assert StoragePathService.clean_relative("https://techcrunch.com/hero.png") == "https://techcrunch.com/hero.png"
    
    # None or empty
    assert StoragePathService.clean_relative(None) is None
    assert StoragePathService.clean_relative("") is None

def test_to_public_url():
    assert StoragePathService.to_public_url("thumbnails/a.webp") == f"{settings.UPLOAD_PUBLIC_PREFIX}/thumbnails/a.webp"
    assert StoragePathService.to_public_url("/images/fallback.webp") == "/images/fallback.webp"
    assert StoragePathService.to_public_url(None) is None

def test_to_filesystem_path():
    expected_path = str(Path(settings.UPLOAD_DIR) / "thumbnails/a.webp")
    assert StoragePathService.to_filesystem_path("thumbnails/a.webp") == expected_path
    assert StoragePathService.to_filesystem_path("/images/fallback.webp") is None
    assert StoragePathService.to_filesystem_path(None) is None

def test_from_public_url():
    assert StoragePathService.from_public_url(f"{settings.UPLOAD_PUBLIC_PREFIX}/thumbnails/a.webp") == "thumbnails/a.webp"
    assert StoragePathService.from_public_url("/images/fallback.webp") == "/images/fallback.webp"
    assert StoragePathService.from_public_url(None) is None
