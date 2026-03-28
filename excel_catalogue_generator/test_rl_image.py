import io
import urllib.request
from reportlab.platypus import Image
from pillow_heif import register_heif_opener
from PIL import Image as PILImage

# Register HEIF opener
register_heif_opener()

def test_reportlab_image():
    # Example file ID: 1XiHynevaRP26TXtYq6AM9eyqhJTQ7uaj (HEIC)
    file_id = "1XiHynevaRP26TXtYq6AM9eyqhJTQ7uaj"
    direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    print(f"Testing ReportLab Image for ID: {file_id}")
    
    try:
        req = urllib.request.Request(direct_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read()
            print(f"Downloaded {len(data)} bytes")
            
            img_io = io.BytesIO(data)
            
            # Test PIL first
            print("Testing PIL opening...")
            pil_img = PILImage.open(img_io)
            print(f"PIL Image size: {pil_img.size}, format: {pil_img.format}")
            
            # Test ReportLab Image
            print("Testing ReportLab Image object...")
            img_io.seek(0)
            rl_img = Image(img_io)
            print(f"ReportLab Image created: {rl_img.drawWidth}x{rl_img.drawHeight}")
            
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_reportlab_image()
