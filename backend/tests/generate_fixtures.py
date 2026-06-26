import os

from PIL import Image, ImageDraw

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets", "images")
os.makedirs(ASSETS_DIR, exist_ok=True)

def create_valid_image():
    img = Image.new("RGB", (800, 600), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((10,10), "Valid Image", fill=(255, 255, 0))
    img.save(os.path.join(ASSETS_DIR, "valid.jpg"), "JPEG")

def create_near_duplicate():
    img = Image.new("RGB", (800, 600), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((10,10), "Valid Image", fill=(255, 255, 0))
    # near duplicate: resize it and change quality
    img = img.resize((400, 300))
    img.save(os.path.join(ASSETS_DIR, "near_duplicate.jpg"), "JPEG", quality=70)

def create_transparent_png():
    img = Image.new("RGBA", (800, 600), (255, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((10,10), "Transparent PNG", fill=(255, 255, 0, 255))
    img.save(os.path.join(ASSETS_DIR, "transparent.png"), "PNG")

def create_animated_gif():
    images = []
    for i in range(2):
        img = Image.new("RGB", (800, 600), color=(i*50, 109, 137))
        d = ImageDraw.Draw(img)
        d.text((10,10), f"Frame {i}", fill=(255, 255, 0))
        images.append(img)
    images[0].save(os.path.join(ASSETS_DIR, "animated.gif"), save_all=True, append_images=images[1:], optimize=False, duration=100, loop=0)

def create_svg():
    svg_content = '<svg height="600" width="800"><text x="10" y="20" fill="red">SVG Test</text></svg>'
    with open(os.path.join(ASSETS_DIR, "svg.svg"), "w") as f:
        f.write(svg_content)

def create_text():
    with open(os.path.join(ASSETS_DIR, "text.txt"), "w") as f:
        f.write("This is a text file, not an image.")

def create_html():
    with open(os.path.join(ASSETS_DIR, "html.html"), "w") as f:
        f.write("<html><body><h1>Not an image</h1></body></html>")

def create_corrupt():
    with open(os.path.join(ASSETS_DIR, "corrupt.jpg"), "wb") as f:
        f.write(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xFF\xDB\x00C\x00This is completely broken")

def create_exif_rotated():
    img = Image.new("RGB", (800, 600), color=(100, 200, 100))
    d = ImageDraw.Draw(img)
    d.text((10,10), "Rotated Image", fill=(0, 0, 0))
    # We write fake EXIF orientation = 8 (Left Bottom)
    # The simplest way is to use piexif or just save normally since PIL handles EXIF natively via info.
    # Actually, we can just use exif parameter in save if we construct a valid EXIF dict.
    # Using raw bytes for simplicity of test:
    # We will just save a valid image and then modify its orientation? 
    # Or just save it with piexif. Since piexif isn't guaranteed installed, let's just make it a standard JPEG for now and assume the pipeline reads whatever orientation it has. Let's just create a normal image for this test and verify it processes it.
    try:
        import piexif
        exif_dict = {"0th": {piexif.ImageIFD.Orientation: 8}}
        exif_bytes = piexif.dump(exif_dict)
        img.save(os.path.join(ASSETS_DIR, "rotated_exif.jpg"), "JPEG", exif=exif_bytes)
    except ImportError:
        img.save(os.path.join(ASSETS_DIR, "rotated_exif.jpg"), "JPEG")

def create_bomb():
    # To simulate a decompression bomb (e.g. 50MB) without using actual disk space until needed, 
    # we can create an image with dimensions that exceed standard thresholds.
    # PIL throws DecompressionBombError if > max_image_pixels. We will create a large empty file for size check.
    # We'll just create a file that's 15MB of random bytes so the downloader rejects it based on size.
    with open(os.path.join(ASSETS_DIR, "bomb.jpg"), "wb") as f:
        f.write(b"0" * 15 * 1024 * 1024)

if __name__ == "__main__":
    create_valid_image()
    create_near_duplicate()
    create_transparent_png()
    create_animated_gif()
    create_svg()
    create_text()
    create_html()
    create_corrupt()
    create_exif_rotated()
    create_bomb()
    print("Fixtures created.")
