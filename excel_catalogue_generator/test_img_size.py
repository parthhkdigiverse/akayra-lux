import io
import urllib.request
import gdown
import re

def test_download():
    # Example file ID from previous logs: 1XiHynevaRP26TXtYq6AM9eyqhJTQ7uaj
    file_id = "1XiHynevaRP26TXtYq6AM9eyqhJTQ7uaj"
    direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    print(f"Testing download for ID: {file_id}")
    
    # Try urllib
    try:
        req = urllib.request.Request(direct_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read()
            print(f"Urllib download size: {len(data)} bytes")
            if len(data) < 2000:
                print("Content snippet:", data[:200].decode('utf-8', errors='ignore'))
    except Exception as e:
        print(f"Urllib failed: {e}")

    # Try gdown
    try:
        output = io.BytesIO()
        gdown.download(id=file_id, output=output, quiet=True)
        print(f"Gdown download size: {output.getbuffer().nbytes} bytes")
    except Exception as e:
        print(f"Gdown failed: {e}")

if __name__ == "__main__":
    test_download()
