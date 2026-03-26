import pandas as pd
import os
import io
import time
import urllib.request
import urllib.error
import gdown
import re
from urllib.parse import urlparse, parse_qs
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer, PageBreak, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from pillow_heif import register_heif_opener

# Register HEIF opener to handle .HEIC files (iPhone format)
register_heif_opener()

class RoundedBadge(Flowable):
    def __init__(self, text):
        Flowable.__init__(self)
        self.text = text
        self.style = ParagraphStyle('BadgeStyle', fontSize=15, fontName='Helvetica', textColor=colors.black)
        self.p = Paragraph(self.text, self.style)

    def wrap(self, availWidth, availHeight):
        w, h = self.p.wrap(availWidth, availHeight)
        self.width = w + 16
        self.height = 24
        return self.width, self.height

    def draw(self):
        self.canv.saveState()
        self.canv.setFillColor(colors.HexColor('#fedac2'))
        self.canv.setStrokeColor(colors.HexColor('#fedac2'))
        self.canv.roundRect(0, 0, self.width, self.height, 6, fill=1, stroke=0)
        self.p.drawOn(self.canv, 8, (self.height - 18)/2.0 - 1)
        self.canv.restoreState()

class ImageBox(Flowable):
    def __init__(self, img_flowable, width, height, bg_color='#e8e8e8', radius=12):
        Flowable.__init__(self)
        self.img = img_flowable
        self.width = width
        self.height = height
        self.bg_color = bg_color
        self.radius = radius

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        self.canv.saveState()
        self.canv.setFillColor(colors.HexColor(self.bg_color))
        self.canv.setStrokeColor(colors.HexColor(self.bg_color))
        self.canv.roundRect(0, 0, self.width, self.height, self.radius, fill=1, stroke=0)
        img_w, img_h = self.img.wrap(self.width, self.height)
        self.img.drawOn(self.canv, (self.width - img_w)/2.0, (self.height - img_h)/2.0)
        self.canv.restoreState()

def get_direct_google_drive_link(url):
    """Converts a standard Google Drive sharing link into a direct download link."""
    if not isinstance(url, str) or not url.strip():
        return None
        
    try:
        parsed_url = urlparse(url)
        if "drive.google.com" in parsed_url.netloc:
            # Handle /file/d/ID/view links
            if "/file/d/" in parsed_url.path:
                file_id = parsed_url.path.split('/file/d/')[1].split('/')[0]
                return f"https://drive.google.com/uc?export=download&id={file_id}"
            
            # Handle ?id=ID links
            query_params = parse_qs(parsed_url.query)
            if 'id' in query_params:
                file_id = query_params['id'][0]
                return f"https://drive.google.com/uc?export=download&id={file_id}"
    except Exception:
        pass
    
    return url

def get_drive_folder_map(folder_url):
    """Parses a public Google Drive folder page for file IDs and names."""
    if not folder_url or "YOUR_FOLDER_ID_HERE" in folder_url:
        return {}
        
    print(f"Mapping Google Drive folder: {folder_url}")
    try:
        # Extract folder ID
        if "/folders/" in folder_url:
            folder_id = folder_url.split("/folders/")[1].split("?")[0].split("/")[0]
        else:
            folder_id = folder_url
            
        # Use the embedded view which is more predictable for scraping
        embed_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
        req = urllib.request.Request(embed_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
        # Regex to find name-ID pairs in the embedded view
        # Fallback 1: entry-ID ... followed by the filename in a class or aria-label
        # We look for entry-ID then any tag until we find a filename with extension
        pairs = re.findall(r'entry-([a-zA-Z0-9\-_]{28,}).+?(?:\>|\")( [^\"]+\.[a-zA-Z0-9]{3,4})[\"<]', html, re.DOTALL)
        
        # Fallback 2: ["ID","FILENAME",null,"TYPE"]
        if not pairs:
             pairs = re.findall(r'\[\"([a-zA-Z0-9\-_]{28,})\"\,\"([^\"]+\.[a-zA-Z0-9]{3,4})\"', html)
             
        file_map = {}
        for fid, name in pairs:
            lname = name.strip().lower()
            if lname.endswith(('.heic', '.jpg', '.png', '.jpeg', '.webp')):
                file_map[lname] = fid
                
        if len(file_map) > 0:
            print(f"Found {len(file_map)} high-res images in cloud folder.")
        else:
            print("No images found. Check if the folder is public ('Anyone with link').")
            
        return file_map
    except Exception as e:
        print(f"⚠️ Error mapping Drive folder: {e}")
        return {}

def download_image(url_or_name, item_name, drive_map=None):
    """Downloads an image from a URL or fetches it from the Google Drive map."""
    if pd.isna(url_or_name) or not str(url_or_name).strip():
        return None
        
    val = str(url_or_name).strip()
    
    # 1. Check if the value is a filename that exists in our Drive map
    if drive_map and val.lower() in drive_map:
        file_id = drive_map[val.lower()]
        direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    elif val.startswith(('http://', 'https://')):
        # 2. Otherwise treat as a direct URL
        direct_url = get_direct_google_drive_link(val)
    else:
        # 3. If it's just a filename but not in the map
        return None
    
    try:
        req = urllib.request.Request(
            direct_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        response = urllib.request.urlopen(req, timeout=15)
        return io.BytesIO(response.read())
    except Exception as e:
        print(f"Failed to fetch image for {item_name}: {e}")
        return None

def generate_catalogue(sheet_url, drive_folder_url, output_pdf="catalogue.pdf"):
    print(f"Fetching data from: {sheet_url}")
    # Initialize Drive Folder Mapping
    drive_map = get_drive_folder_map(drive_folder_url)
    
    try:
        df = pd.read_csv(sheet_url)
        df = df.dropna(how='all')
        print(f"Successfully fetched {len(df)} row(s) from Google Sheets.")
        if len(df) > 0:
            print("First 3 items found in the data:")
            for i, row in df.head(3).iterrows():
                brand = str(row.get('Brand', 'N/A'))
                item_type = str(row.get('Type', 'N/A'))
                print(f"   - {brand} {item_type}")
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    page_width, page_height = landscape(A4)

    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=landscape(A4),
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'ItemTitle',
        parent=styles['Heading1'],
        fontSize=24,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=15
    )
    
    detail_style = ParagraphStyle(
        'ItemDetail',
        parent=styles['Normal'],
        fontSize=15,
        fontName='Helvetica',
        textColor=colors.HexColor('#333333'),
        leading=24
    )
    
    price_style = ParagraphStyle(
        'ItemPrice',
        parent=styles['Normal'],
        fontSize=22,
        textColor=colors.HexColor('#9e1c1c'),
        fontName='Helvetica-Bold'
    )
    
    footer_style = ParagraphStyle(
        'ItemFooter',
        parent=styles['Normal'],
        fontSize=18,
        fontName='Helvetica-Oblique',
        textColor=colors.HexColor('#c48b4b'), # Orange
        alignment=0 # Left
    )
    
    # Styles for dynamic header
    header_logo_style = ParagraphStyle(
        'HeaderLogo',
        parent=styles['Normal'],
        fontSize=16,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2c3e50'),
        alignment=0 # Left
    )
    
    header_uid_style = ParagraphStyle(
        'HeaderUID',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#7f8c8d'),
        alignment=1 # Center
    )
    
    header_contact_style = ParagraphStyle(
        'HeaderContact',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#34495e'),
        alignment=2 # Right
    )
    
    gen_time_str = time.strftime("%Y-%m-%d %H:%M:%S")

    story = []

    def clean_val(v, default="N/A"):
        if pd.isna(v) or str(v).strip().lower() == 'nan' or str(v).strip() == '':
            return default
        val_str = str(v).strip()
        if val_str.endswith('.0'):
            return val_str[:-2]
        return val_str

    for index, row in df.iterrows():
        # Extracted fields based on CSV columns
        uid = clean_val(row.get('UID'))
        brand = clean_val(row.get('Brand'), 'Unknown')
        item_type = clean_val(row.get('Type'), '')
        size = clean_val(row.get('Size'))
        color = clean_val(row.get('Color'))
        orig_price = clean_val(row.get('Original Price'))
        sell_price = clean_val(row.get('Selling Price'))
        unit = clean_val(row.get('Unit'), '')
        
        if unit == '0':
            continue
        
        # prefer 'AI Photo', then 'Perfect Photo Or Link', then 'Photo'
        ai_photo = row.get('AI Photo', '')
        perfect_photo = row.get('Perfect Photo Or Link', '')
        photo = row.get('Photo', '')
        
        img_url = None
        for p in [ai_photo, perfect_photo, photo]:
            if pd.notna(p) and str(p).strip():
                img_url = str(p).strip()
                break
        
        # 1. GENERATE DYNAMIC PAGE HEADER FOR THIS ITEM
        logo_path = "akayra_logo.png"
        if os.path.exists(logo_path):
            # Scale logo to reasonable header size (e.g., 1.2 inches wide)
            logo_img = Image(logo_path)
            logo_aspect = logo_img.imageWidth / float(logo_img.imageHeight)
            logo_img.drawWidth = 1.2 * inch
            logo_img.drawHeight = (1.2 * inch) / logo_aspect
            logo_p = logo_img
        else:
            logo_p = Paragraph("[ COMPANY LOGO ]", header_logo_style)
            
        uid_p = Paragraph(f"Product UID: {uid}<br/><font size='8' color='#999999'>Generated: {gen_time_str}</font>", header_uid_style)
        contact_p = Paragraph("Akayra Lux<br/>akayra.lux@gmail.com<br/>+91 73598 04120", header_contact_style)
        
        header_table = Table(
            [[logo_p, uid_p, contact_p]],
            colWidths=[
                (page_width - 80) * 0.3,
                (page_width - 80) * 0.4,
                (page_width - 80) * 0.3
            ]
        )
        
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor('#e0e0e0')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 15),
        ]))
        
        story.append(header_table)
        story.append(Spacer(1, 40))
        
        # 2. GENERATE ITEM CONTENT
        # Build Text details
        name_text = f"{brand} {item_type}".strip().upper()
        
        orig_price_str = f"<strike>{orig_price}</strike>" if orig_price != "N/A" else "N/A"

        detail_data = [
            [Paragraph("<font color='#000000'>Type:</font>", detail_style), Paragraph(item_type, detail_style)],
            [Paragraph("<font color='#000000'>Size:</font>", detail_style), Paragraph(size, detail_style)],
            [Paragraph("<font color='#000000'>Color:</font>", detail_style), Paragraph(color, detail_style)],
            [Paragraph("<font color='#000000'>Original:</font>", detail_style), Paragraph(orig_price_str, detail_style)]
        ]
        
        detail_table = Table(detail_data, colWidths=[80, 250])
        detail_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
        ]))
        
        price_html = f"Our Price: {sell_price}"
        
        text_elements = [
            Paragraph(name_text, title_style),
            Spacer(1, 15),
            detail_table,
            Spacer(1, 25),
            Paragraph(price_html, price_style)
        ]
        
        if unit and unit not in ["N/A", "0"]:
            footer_text = f"Hurry Up! Only {unit} pieces left"
            text_elements.extend([Spacer(1, 20), Paragraph(footer_text, footer_style)])
            
        text_content = text_elements
        
        # Build Image
        image_content = []
        if img_url:
            print(f"Processing image for {name_text}...")
            img_data = download_image(img_url, name_text, drive_map)
            if img_data:
                try:
                    # reportlab Image takes a file-like object
                    rl_img = Image(img_data)
                    # Maximize image size to fill left half of the page
                    max_width = (page_width - 120) / 2.0  # Column width minus padding
                    max_height = page_height - 200        # Page height minus margin/header
                    
                    aspect = rl_img.imageWidth / float(rl_img.imageHeight)
                    
                    # Fit within bounds while preserving aspect ratio
                    box_padding = 20
                    actual_max_width = max_width - box_padding * 2
                    actual_max_height = max_height - box_padding * 2
                    
                    if (actual_max_width / aspect) <= actual_max_height:
                        rl_img.drawWidth = actual_max_width
                        rl_img.drawHeight = actual_max_width / aspect
                    else:
                        rl_img.drawHeight = actual_max_height
                        rl_img.drawWidth = actual_max_height * aspect
                        
                    rounded_box = ImageBox(rl_img, rl_img.drawWidth + box_padding*2, rl_img.drawHeight + box_padding*2)
                    image_content.append(rounded_box)
                except Exception as e:
                    print(f"Error processing image for {name_text}: {e}")
                    image_content.append(Paragraph("<i>Image format error</i>", styles['Normal']))
            else:
                 image_content.append(Paragraph("<i>Image download failed</i>", styles['Normal']))
        else:
             image_content.append(Paragraph("<i>No Image Available</i>", styles['Normal']))
             
        
        # Create a table for this item (Image Left, Details Right)
        col_width = (page_width - 80) / 2.0
        
        if not image_content:
            image_content = [Paragraph("<i>Error</i>", styles['Normal'])]
            
        item_table = Table([[image_content, text_content]], colWidths=[col_width, col_width])
        item_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 20),
        ]))
        
        story.append(item_table)
        story.append(Spacer(1, 40))
        
        bottom_line = Table([[""]], colWidths=[page_width - 80])
        bottom_line.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,-1), 1.0, colors.HexColor('#e0e0e0'))
        ]))
        story.append(bottom_line)
        
        story.append(PageBreak())

    print("Building PDF...")
    try:
        # Build without the static on_page_header
        doc.build(story)
        print(f"Successfully generated PDF catalogue: {os.path.abspath(output_pdf)}")
    except Exception as e:
        print(f"Error generating PDF: {e}")


if __name__ == "__main__":
    # Your Google Sheet Link
    google_sheet_url = "https://docs.google.com/spreadsheets/d/1B36VgxQtWhbVRpVv2ZtSEj1tJvcZ5iOg3jxn0lj3UC8/edit?usp=sharing"
    
    # [ACTION REQUIRED] Paste your Public Google Drive Folder Link here
    GOOGLE_DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/1hsg2UdJDhzWySvGo7YjMJr9l6LZtmK-o?usp=sharing"
    
    # We will automatically convert the sharing link into a direct CSV download link
    def get_csv_export_url(url):
        if '/edit' in url:
            # Replaces anything after /edit with /export?format=csv
            # We add &t={int(time.time())} as a cache-buster so Google always sends the fresh version
            base_url = url.split('/edit')[0]
            return f"{base_url}/export?format=csv&t={int(time.time())}"
        return url
    
    csv_url = get_csv_export_url(google_sheet_url)
    output_pdf_path = "catalogue.pdf"
    generate_catalogue(csv_url, GOOGLE_DRIVE_FOLDER_URL, output_pdf_path)
