import requests
import re
import json

def get_drive_folder_map_regex(folder_url):
    """Parses a public Google Drive folder page for file IDs and names."""
    if not folder_url or "YOUR_FOLDER_ID_HERE" in folder_url:
        return {}
    
    # Extract folder ID
    if "/folders/" in folder_url:
        folder_id = folder_url.split("/folders/")[1].split("?")[0].split("/")[0]
    else:
        folder_id = folder_url
        
    print(f"Scraping Drive folder ID: {folder_id}")
    # Using the 'embeddedfolderview' which is more likely to have a clean JSON structure
    embed_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
    
    try:
        r = requests.get(embed_url, headers={'User-Agent': 'Mozilla/5.0'})
        
        # In the embed view, mapping is found in a JSON structure like:
        # ["ID", "Name", null, "Type", ...]
        # We look for ID (33 chars) followed by the filename
        # Example pattern: ["1abc...33ID","IMG_xxx.HEIC"
        
        pairs = re.findall(r'\["([a-zA-Z0-9\-_]{33})","([^"]+)"', r.text)
        
        file_map = {}
        for fid, name in pairs:
            # Filter for common image extensions just in case
            lname = name.strip().lower()
            if lname.endswith(('.heic', '.jpg', '.png', '.jpeg', '.webp')):
                file_map[lname] = fid
            
        return file_map

    except Exception as e:
        print(f"Error: {e}")
        return {}

if __name__ == "__main__":
    url = "https://drive.google.com/drive/folders/1hsg2UdJDhzWySvGo7YjMJr9l6LZtmK-o?usp=sharing"
    result = get_drive_folder_map_regex(url)
    print(f"✅ Found {len(result)} files:")
    for k, v in list(result.items())[:10]:
        print(f"  {k} -> {v}")
