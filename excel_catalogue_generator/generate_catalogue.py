import pandas as pd
import os
import io
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse, parse_qs
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

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

def download_image(url):
    """Downloads an image from a URL and returns an io.BytesIO object, or None if failed."""
    if pd.isna(url) or not str(url).strip():
        return None
        
    url = str(url).strip()
    direct_url = get_direct_google_drive_link(url)
    
    try:
        # Add a headers dictionary with a User-Agent to avoid 403 Forbidden
        req = urllib.request.Request(
            direct_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        response = urllib.request.urlopen(req, timeout=10)
        return io.BytesIO(response.read())
    except Exception as e:
        print(f"Failed to download image from {url}: {e}")
        return None

def generate_catalogue(sheet_url, output_pdf="catalogue.pdf"):
    print(f"Fetching data from: {sheet_url}")
    try:
        df = pd.read_csv(sheet_url)
        df = df.dropna(how='all')
        print(f"✅ Successfully fetched {len(df)} row(s) from Google Sheets.")
        if len(df) > 0:
            print("📋 First 3 items found in the data:")
            for i, row in df.head(3).iterrows():
                brand = str(row.get('Brand', 'N/A'))
                item_type = str(row.get('Type', 'N/A'))
                print(f"   - {brand} {item_type}")
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
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
        textColor=colors.HexColor('#d32f2f'),
        fontName='Helvetica-Bold',
        spaceBefore=25
    )
    
    footer_style = ParagraphStyle(
        'ItemFooter',
        parent=styles['Normal'],
        fontSize=18,
        fontName='Helvetica-Oblique',
        textColor=colors.HexColor('#e67e22'), # Orange
        alignment=1, # Center
        spaceBefore=25
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
        
        # Strikethrough for original price if it exists
        orig_price_str = f"<strike>{orig_price}</strike>" if orig_price != "N/A" else "N/A"

        details_html = f"""
        <font color="#888888">Type:</font> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {item_type}<br/>
        <font color="#888888">Size:</font> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {size}<br/>
        <font color="#888888">Color:</font> &nbsp;&nbsp;&nbsp;&nbsp; {color}<br/>
        <font color="#888888">Original:</font> &nbsp; {orig_price_str}<br/>
        """
        
        price_html = f"Our Price: {sell_price}"
        
        text_content = [
            Paragraph(name_text, title_style),
            Paragraph(details_html, detail_style),
            Paragraph(price_html, price_style)
        ]
        
        # Build Image
        image_content = []
        if img_url:
            print(f"Downloading image for {name_text}...")
            img_data = download_image(img_url)
            if img_data:
                try:
                    # reportlab Image takes a file-like object
                    rl_img = Image(img_data)
                    # Maximize image size to fill left half of the page
                    max_width = (page_width - 120) / 2.0  # Column width minus padding
                    max_height = page_height - 200        # Page height minus margin/header
                    
                    aspect = rl_img.imageWidth / float(rl_img.imageHeight)
                    
                    # Fit within bounds while preserving aspect ratio
                    if (max_width / aspect) <= max_height:
                        rl_img.drawWidth = max_width
                        rl_img.drawHeight = max_width / aspect
                    else:
                        rl_img.drawHeight = max_height
                        rl_img.drawWidth = max_height * aspect
                        
                    image_content.append(rl_img)
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
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#eeeeee')),
            ('LINEAFTER', (0,0), (0,-1), 1, colors.HexColor('#eeeeee')),
            ('PADDING', (0,0), (-1,-1), 30),
            ('BACKGROUND', (0,0), (-1,-1), colors.white),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#fafafa')), # Light gray behind image
        ]))
        
        story.append(item_table)
        
        if unit and unit not in ["N/A", "0"]:
            footer_text = f"Hurry Up! Only {unit} pieces left"
            story.append(Paragraph(footer_text, footer_style))
            
        story.append(PageBreak())

    print("Building PDF...")
    try:
        # Build without the static on_page_header
        doc.build(story)
        print(f"✅ Successfully generated PDF catalogue: {os.path.abspath(output_pdf)}")
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")


if __name__ == "__main__":
    google_sheet_url = "https://docs.google.com/spreadsheets/d/1ptPQnyNY0u17OZ-cBlRC6bbq46--bMobL4Xog5wML7E/edit?usp=sharing"
    
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
    generate_catalogue(csv_url, output_pdf_path)
