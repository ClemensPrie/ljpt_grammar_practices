"""Build the JLPT Grammar Practice app (index.html with embedded data)."""
import json, csv, struct, zlib
from pathlib import Path

DIR = Path(__file__).parent


def make_png_icon(size, filepath):
    """Generate a solid dark PNG with a red circle border (no text - keeps it simple)."""
    bg = (15, 15, 26)       # #0f0f1a
    fg = (233, 69, 96)      # #e94560
    cx, cy = size // 2, size // 2
    r_outer = int(size * 0.39)
    r_inner = int(size * 0.35)
    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if r_inner <= d <= r_outer:
                row.extend(fg)
            else:
                row.extend(bg)
        rows.append(b'\x00' + bytes(row))  # filter byte + RGB
    raw = b''.join(rows)
    # PNG structure
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    ihdr = struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)
    idat = zlib.compress(raw, 9)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b'')
    filepath.write_bytes(png)


# Generate icons
make_png_icon(192, DIR / "icon-192.png")
make_png_icon(512, DIR / "icon-512.png")
print("Generated icon-192.png and icon-512.png")

# Load grammar
with open(DIR / "grammar_entries.json", encoding="utf-8") as f:
    gdata = json.load(f)

# Load vocab
vdata = []
for fn in ["n5.csv", "n4.csv", "n3.csv"]:
    with open(DIR / fn, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            row["_source"] = fn.replace(".csv", "")
            vdata.append(row)

# Load topic data
tdata = {}
for fn in ["n5_expressions_slim.json", "n4_expressions_slim.json", "n3_expressions_slim.json"]:
    path = DIR / "data" / "topic_json" / fn
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            level = data.get("level", fn.replace("_expressions_slim.json", ""))
            tdata[level] = data.get("topics", {})

gj = json.dumps(gdata, ensure_ascii=False)
vj = json.dumps(vdata, ensure_ascii=False)
tj = json.dumps(tdata, ensure_ascii=False)

# Read the template HTML and substitute placeholders
template = (DIR / "app_template.html").read_text(encoding="utf-8")
html = template.replace("{{GRAMMAR_JSON}}", gj).replace("{{VOCAB_JSON}}", vj).replace("{{TOPICS_JSON}}", tj)

(DIR / "index.html").write_text(html, encoding="utf-8")

print(f"Written: {DIR / 'index.html'}")
print(f"Grammar: {len(gdata)}, Vocab: {len(vdata)}, Topics: {len(tdata)}")
print(f"Size: {(DIR / 'index.html').stat().st_size // 1024} KB")
