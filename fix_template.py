"""Patch app_template.html: PWA support, offline SW, tighter LLM prompts. Run once."""
from pathlib import Path

p = Path("/Workspace/Users/clemens.priessnitz@oebb.at/databricks_apps/test/app_template.html")
content = p.read_text(encoding="utf-8")

# --- Fix 1: Text mode prompt - specify exact vocab format ---
old_vocab = '"vocab": [{ALL kanji-containing words from the text with readings and meanings}]'
new_vocab = '"vocab": [{"word": "kanji form", "reading": "hiragana", "meaning": "English"}]'
if old_vocab in content:
    content = content.replace(old_vocab, new_vocab)
    print("[1] Fixed text mode vocab format in prompt")
else:
    print("[1] Vocab format already fixed or not found")

# --- Fix 2: rV fallback keys ---
old_rV = (
    "function rV(v){var word=v&&v.word!=null?String(v.word):'';"
    "var reading=v&&v.reading!=null?String(v.reading):'';"
    "var meaning=v&&v.meaning!=null?String(v.meaning):'';"
)
new_rV = (
    "function rV(v){if(!v)return '';"
    "var word=String(v.word||v.kanji||v.expression||'');"
    "var reading=String(v.reading||v.kana||'');"
    "var meaning=String(v.meaning||v.english||v.translation||'');"
)
if old_rV in content:
    content = content.replace(old_rV, new_rV)
    print("[2] Fixed rV fallback keys")
else:
    print("[2] rV already patched or not found")

# --- Fix 3: Add one-shot example + strict key instruction to text mode prompt ---
# Insert after the vocab format line in text mode
old_text_end = (
    '"grammars": [list of grammar patterns you used]\\n}\';return t}'
)
new_text_end = (
    '"grammars": ["grammar1", "grammar2"]\\n}\\n\\n'
    'IMPORTANT: Each vocab item MUST use exactly these keys: word, reading, meaning. '
    'The "word" field must contain the kanji form. If a word has no kanji, put kana in "word" and leave "reading" empty. '
    'Example: {"word": "食べる", "reading": "たべる", "meaning": "to eat"}\';return t}'
)
if old_text_end in content:
    content = content.replace(old_text_end, new_text_end)
    print("[3] Added one-shot example + strict keys to text prompt")
else:
    print("[3] Text prompt end not found (may already be patched)")

# --- Fix 4: Add strict key instruction to sentence mode prompt ---
old_sent_end = "t+='vocab items format: {word: \"kanji word\", reading: \"hiragana\", meaning: \"English\"}';return t}"
new_sent_end = (
    "t+='vocab items format: {\"word\": \"kanji form\", \"reading\": \"hiragana\", \"meaning\": \"English\"}\\n"
    "IMPORTANT: Use ONLY these keys. The word field must be the kanji form. "
    "Example: {\"word\": \"食べる\", \"reading\": \"たべる\", \"meaning\": \"to eat\"}';return t}"
)
if old_sent_end in content:
    content = content.replace(old_sent_end, new_sent_end)
    print("[4] Added strict keys to sentence prompt")
else:
    print("[4] Sentence prompt end not found (may already be patched)")

# --- Fix 5: PWA meta tags in <head> ---
pwa_meta = (
    '<link rel=manifest href=manifest.json>\n'
    '<meta name=apple-mobile-web-app-capable content=yes>\n'
    '<meta name=apple-mobile-web-app-status-bar-style content=black-translucent>\n'
    '<link rel=apple-touch-icon href=icon-192.png>\n'
)
if 'rel=manifest' not in content:
    content = content.replace('<title>JLPT Grammar Practice</title>', pwa_meta + '<title>JLPT Grammar Practice</title>')
    print("[5] Added PWA meta tags")
else:
    print("[5] PWA meta already present")

# --- Fix 6: Register service worker at end of script ---
sw_reg = "if('serviceWorker' in navigator){navigator.serviceWorker.register('sw.js')}"
if 'serviceWorker' not in content:
    content = content.replace('bGC(\'N4\');lSU();', 'bGC(\'N4\');lSU();' + sw_reg)
    print("[6] Added service worker registration")
else:
    print("[6] SW registration already present")

p.write_text(content, encoding="utf-8")
print("\nDone. Now run build_app.py to regenerate index.html.")
