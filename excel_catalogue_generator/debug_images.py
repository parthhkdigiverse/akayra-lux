import pandas as pd
import time
import urllib.request
import os

google_sheet_url = "https://docs.google.com/spreadsheets/d/1B36VgxQtWhbVRpVv2ZtSEj1tJvcZ5iOg3jxn0lj3UC8/edit?usp=sharing"

def get_csv_export_url(url):
    if '/edit' in url:
        base_url = url.split('/edit')[0]
        return f"{base_url}/export?format=csv&t={int(time.time())}"
    return url

csv_url = get_csv_export_url(google_sheet_url)
print(f"Fetching: {csv_url}")

try:
    df = pd.read_csv(csv_url)
    print(f"Found {len(df)} rows")
    print(df.columns.tolist())
    
    subset = df[['Brand', 'Type', 'AI Photo', 'Perfect Photo Or Link', 'Photo', 'Unit']].dropna(how='all')
    print("\nFirst 10 rows:")
    print(subset.head(10).to_string())
    
    # Check image patterns
    all_photos = subset['AI Photo'].tolist() + subset['Perfect Photo Or Link'].tolist() + subset['Photo'].tolist()
    unique_photos = set([p for p in all_photos if pd.notna(p) and str(p).strip()])
    print(f"\nTotal unique Photo strings: {len(unique_photos)}")
    for p in list(unique_photos)[:10]:
        print(f" - {p}")
        
except Exception as e:
    print(f"Error: {e}")
