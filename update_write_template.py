"""Encode app_template.html as base64 and write a self-extracting script."""
import base64
from pathlib import Path

DIR = Path("/Workspace/Users/clemens.priessnitz@oebb.at/databricks_apps/test")

# Read the updated template
content = (DIR / "app_template.html").read_bytes()
encoded = base64.b64encode(content).decode()

# Create write_template.py with the encoded template
write_template_code = f'''import base64
t = base64.b64decode("""{encoded}""").decode("utf-8")
with open("app_template.html", "w", encoding="utf-8") as f:
    f.write(t)
print("Template written to app_template.html")
'''

(DIR / "write_template.py").write_text(write_template_code, encoding="utf-8")
print(f"Updated write_template.py ({len(encoded)} encoded chars)")
