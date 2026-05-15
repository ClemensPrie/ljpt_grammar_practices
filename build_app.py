"""Build the JLPT Grammar Practice app (index.html with embedded data)."""
import json, csv
from pathlib import Path

DIR = Path("/Workspace/Users/clemens.priessnitz@oebb.at/databricks_apps/test")

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
