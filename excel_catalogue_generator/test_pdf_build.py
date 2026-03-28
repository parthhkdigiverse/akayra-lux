import io
from reportlab.platypus import SimpleDocTemplate, Image, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from pillow_heif import register_heif_opener
from PIL import Image as PILImage
import urllib.request

register_heif_opener()

def test_full_build():
    file_id = "1XiHynevaRP26TXtYq6AM9eyqhJTQ7uaj"
    direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    doc = SimpleDocTemplate("test_output.pdf", pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    try:
        req = urllib.request.Request(direct_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read()
            print(f"Downloaded {len(data)} bytes")
            
            # --- ATTEMPT 1: Raw HEIC ---
            # story.append(Paragraph("Attempt 1: Raw HEIC", styles['h1']))
            # img_io = io.BytesIO(data)
            # rl_img = Image(img_io, width=200, height=200)
            # story.append(rl_img)
            
            # --- ATTEMPT 2: Converted JPEG ---
            story.append(Paragraph("Attempt 2: Converted JPEG", styles['h1']))
            pil_img = PILImage.open(io.BytesIO(data))
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")
            
            img_buffer = io.BytesIO()
            pil_img.save(img_buffer, format="JPEG", quality=80)
            img_buffer.seek(0)
            
            rl_img_fixed = Image(img_buffer, width=400, height=500)
            story.append(rl_img_fixed)
            
            doc.build(story)
            print("PDF built: test_output.pdf")
            
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_build()
