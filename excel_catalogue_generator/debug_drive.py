import urllib.request
import re
import time

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
        
        print(f"Folder ID: {folder_id}")
            
        # Use the embedded view which is more predictable for scraping
        embed_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
        req = urllib.request.Request(embed_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
        print(f"HTML length: {len(html)}")
        
        # Save HTML for inspection
        with open("drive_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        # Regex to find name-ID pairs in the embedded view
        pairs = re.findall(r'id="entry-([a-zA-Z0-9\-_]{20,})".+?<div class="flip-entry-title">([^<]+)</div>', html, re.DOTALL)
        print(f"Regex 1 pairs: {len(pairs)}")
        
        if not pairs:
             pairs = re.findall(r'\[\"([a-zA-Z0-9\-_]{20,})\"\,\"([^\"]+\.[a-zA-Z0-9]{3,4})\"', html)
             print(f"Regex 2 pairs: {len(pairs)}")

        # Try a more generic regex for ID and Filename
        if not pairs:
            # Look for JSON-like structures that contain filenames
            pairs = re.findall(r'\"([a-zA-Z0-9\-_]{20,})\"\,\"([^\"]+\.(?:heic|jpg|jpeg|png|webp))\"', html, re.IGNORECASE)
            print(f"Regex 3 pairs: {len(pairs)}")
            
        file_map = {}
        for fid, name in pairs:
            lname = name.strip().lower()
            file_map[lname] = fid
                
        print(f"Total mapped files: {len(file_map)}")
        if file_map:
            print("First 5 files:")
            for k, v in list(file_map.items())[:5]:
                print(f" - {k}: {v}")
            
        return file_map
    except Exception as e:
        print(f"⚠️ Error mapping Drive folder: {e}")
        return {}

GOOGLE_DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/1hsg2UdJDhzWySvGo7YjMJr9l6LZtmK-o?usp=sharing"
get_drive_folder_map(GOOGLE_DRIVE_FOLDER_URL)
