import re

with open("drive_debug.html", "r", encoding="utf-8") as f:
    html = f.read()

# Try the regex from generate_catalogue.py
pairs = re.findall(r'id="entry-([a-zA-Z0-9\-_]{20,})".+?<div class="flip-entry-title">([^<]+)</div>', html, re.DOTALL)
print(f"Original regex found: {len(pairs)} pairs")
if pairs:
    print(f"First pair: {pairs[0]}")

# Try a more robust regex
robust_pairs = re.findall(r'entry-([a-zA-Z0-9\-_]{20,})[\s\S]+?class="flip-entry-title">([^<]+)<', html)
print(f"Robust regex found: {len(robust_pairs)} pairs")
if robust_pairs:
    print(f"First robust pair: {robust_pairs[0]}")

# Another attempt focusing on the <a> tag href and the title
shared_links = re.findall(r'href="https://drive\.google\.com/file/d/([a-zA-Z0-9\-_]{20,})/view[^"]*".+?<div class="flip-entry-title">([^<]+)</div>', html, re.DOTALL)
print(f"Shared link regex found: {len(shared_links)} pairs")
if shared_links:
    print(f"First shared link pair: {shared_links[0]}")
