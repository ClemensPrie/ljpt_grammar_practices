import pandas as pd
import re
from pathlib import Path
from math import ceil

def load_kanji_meanings(joyo_file='joyo.csv'):
    """Load kanji meanings from joyo.csv into a dict."""
    if not Path(joyo_file).exists():
        return {}
    df = pd.read_csv(joyo_file)
    meanings = {}
    for _, row in df.iterrows():
        kanji = row['kanji']
        meaning = row.get('meanings', '')
        if pd.notna(meaning):
            meanings[kanji] = str(meaning).split('|')[0]
        else:
            meanings[kanji] = ''
    return meanings

def extract_jlpt_level(tags):
    """Extract JLPT level from tags column, preferring explicit JLPT_Nx."""
    if pd.isna(tags) or not isinstance(tags, str):
        return None
    match = re.search(r'JLPT_([Nn][1-5])', tags)
    if match:
        return match.group(1).upper()
    return None

def create_vocab_by_jlpt_html():
    # Load kanji meanings
    kanji_meanings = load_kanji_meanings()
    print(f"Loaded meanings for {len(kanji_meanings)} kanji")
    
    # Load vocabulary files
    vocab_files = {
        'N5': 'n5.csv',
        'N4': 'n4.csv',
        'N3': 'n3.csv',
        'N2': 'n2.csv',
        'N1': 'n1.csv'
    }
    
    all_vocab = []
    for level, filename in vocab_files.items():
        if not Path(filename).exists():
            print(f"Warning: {filename} not found, skipping")
            continue
        df = pd.read_csv(filename)
        df.columns = df.columns.str.lower()
        df['source_level'] = level
        df['extracted_jlpt'] = df['tags'].apply(extract_jlpt_level)
        df['final_jlpt'] = df['extracted_jlpt'].fillna(level)
        all_vocab.append(df)
    
    if not all_vocab:
        print("Error: No vocabulary files found!")
        return
    
    vocab_df = pd.concat(all_vocab, ignore_index=True)
    vocab_df = vocab_df.drop_duplicates(subset=['expression'])
    print(f"Total unique vocabulary entries: {len(vocab_df)}")
    
    # Group by final JLPT level
    level_order = ['N5', 'N4', 'N3', 'N2', 'N1']
    grouped = {level: [] for level in level_order}
    
    for _, row in vocab_df.iterrows():
        level = row['final_jlpt']
        if level in grouped:
            grouped[level].append(row)
        else:
            if 'other' not in grouped:
                grouped['other'] = []
            grouped['other'].append(row)
    
    # Start HTML generation
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>JLPT Vocabulary by Level</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f5f5;
            padding: 16px;
            color: #333;
        }
        .container { max-width: 700px; margin: 0 auto; }
        h1 { font-size: 28px; margin-bottom: 8px; color: #1a1a1a; }
        .subtitle { color: #666; margin-bottom: 24px; font-size: 14px; }
        
        /* Level sections */
        .level-section {
            background: white;
            border-radius: 12px;
            margin-bottom: 16px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .level-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 16px 20px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: bold;
            font-size: 18px;
            user-select: none;
        }
        .level-header.N5 { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .level-header.N4 { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
        .level-header.N3 { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
        .level-header.N2 { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
        .level-header.N1 { background: linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%); }
        .level-badge { background: rgba(255,255,255,0.2); padding: 4px 10px; border-radius: 20px; font-size: 14px; }
        .toggle-icon { font-size: 20px; transition: transform 0.3s; }
        .level-section.collapsed .toggle-icon { transform: rotate(-90deg); }
        .level-content { padding: 16px; display: block; }
        .level-section.collapsed .level-content { display: none; }
        
        /* Group sections (30 words each) */
        .group-section {
            background: #fefefe;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid #e0e0e0;
            overflow: hidden;
        }
        .group-header {
            background: #f0f0f0;
            padding: 10px 14px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 600;
            color: #444;
            border-bottom: 1px solid #e0e0e0;
            user-select: none;
        }
        .group-header:hover { background: #e8e8e8; }
        .group-toggle-icon { font-size: 16px; transition: transform 0.3s; }
        .group-section.collapsed .group-toggle-icon { transform: rotate(-90deg); }
        .group-content { display: block; padding: 12px; }
        .group-section.collapsed .group-content { display: none; }
        
        /* Vocabulary cards */
        .vocab-card {
            background: #fafafa;
            border-radius: 10px;
            margin-bottom: 12px;
            border: 1px solid #e8e8e8;
            overflow: hidden;
        }
        .vocab-header {
            padding: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: white;
            transition: background 0.2s;
        }
        .vocab-header.clickable { cursor: pointer; user-select: none; }
        .vocab-header.clickable:hover { background: #f5f5f5; }
        .vocab-header-left { flex: 1; }
        .word-index {
            display: inline-block;
            background: #e0e0e0;
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 20px;
            margin-right: 10px;
            color: #555;
        }
        .vocab-expression { font-size: 18px; font-weight: 500; font-family: "Hiragino Kaku Gothic Pro", "Noto Sans CJK JP", sans-serif; }
        .vocab-reading { font-size: 12px; color: #888; margin-top: 2px; }
        .vocab-meaning { font-size: 14px; color: #555; margin-top: 4px; }
        .vocab-toggle { font-size: 18px; color: #999; transition: transform 0.3s; margin-left: 12px; }
        .vocab-card.collapsed .vocab-toggle { transform: rotate(-90deg); }
        .vocab-details {
            padding: 0 12px 12px 12px;
            display: block;
            border-top: 1px solid #e8e8e8;
            background: #fafafa;
        }
        .vocab-card.collapsed .vocab-details { display: none; }
        
        .kanji-in-word {
            background: #fff8e7;
            border-radius: 8px;
            padding: 8px 12px;
            margin-top: 8px;
        }
        .kanji-in-word:first-child { margin-top: 0; }
        .small-kanji { font-size: 22px; font-weight: bold; margin-right: 10px; font-family: "Hiragino Kaku Gothic Pro", "Noto Sans CJK JP", sans-serif; }
        .kanji-meaning { font-size: 14px; color: #555; }
        
        .stats {
            background: #e8e8e8;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 16px;
            font-size: 13px;
            text-align: center;
        }
        .search-box {
            width: 100%;
            padding: 12px 16px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 25px;
            margin-bottom: 16px;
            outline: none;
        }
        .search-box:focus { border-color: #667eea; }
        .button-group { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
        .expand-all-btn, .collapse-all-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            cursor: pointer;
        }
        
        @media (max-width: 480px) {
            body { padding: 12px; }
            .vocab-expression { font-size: 16px; }
            .small-kanji { font-size: 20px; }
        }
        @media print {
            body { background: white; padding: 0; }
            .level-header, .group-header, .vocab-header { cursor: default; break-inside: avoid; }
            .level-section.collapsed .level-content, .group-section.collapsed .group-content, .vocab-card.collapsed .vocab-details { display: block; }
            .toggle-icon, .group-toggle-icon, .vocab-toggle, .expand-all-btn, .collapse-all-btn, .search-box, .button-group { display: none; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📖 JLPT Vocabulary</h1>
        <div class="subtitle">Grouped by level & batches of 30 words</div>
        <input type="text" class="search-box" id="searchBox" placeholder="🔍 Search expression, reading, or meaning...">
        <div class="button-group">
            <button class="expand-all-btn" onclick="expandAllLevelsAndGroups()">📖 Expand All</button>
            <button class="collapse-all-btn" onclick="collapseAllLevelsAndGroups()">📕 Collapse All</button>
        </div>
        <div id="levelsContainer">
'''
    
    # Generate HTML for each JLPT level
    for level in level_order:
        if level not in grouped or not grouped[level]:
            continue
        vocab_list = grouped[level]
        total_words = len(vocab_list)
        group_size = 30
        num_groups = ceil(total_words / group_size)
        
        html_content += f'''
        <div class="level-section" id="level-{level}">
            <div class="level-header {level}" onclick="toggleLevel(this.parentElement)">
                <span><span class="level-badge">{level}</span><span>({total_words} words)</span></span>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="level-content">
                <div class="stats">📖 {total_words} vocabulary words (groups of {group_size})</div>
'''
        
        # Split into groups of 30
        for group_idx in range(num_groups):
            start = group_idx * group_size
            end = min(start + group_size, total_words)
            group_words = vocab_list[start:end]
            start_index = start + 1
            end_index = end
            
            html_content += f'''
                <div class="group-section collapsed" id="group-{level}-{group_idx}">
                    <div class="group-header" onclick="toggleGroup(this.parentElement)">
                        <span>📚 Words {start_index}–{end_index} ({len(group_words)} items)</span>
                        <span class="group-toggle-icon">▼</span>
                    </div>
                    <div class="group-content">
'''
            # Write each word in the group
            for pos, row in enumerate(group_words):
                word_index = start + pos + 1
                expression = row['expression']
                reading = row.get('reading', '')
                meaning = row.get('meaning', '')
                
                # Extract kanji characters
                kanji_chars = re.findall(r'[\u4e00-\u9faf]', str(expression))
                has_kanji_details = len(kanji_chars) >= 2
                
                # Build kanji meanings HTML only if at least 2 kanji
                kanji_meanings_html = ''
                if has_kanji_details:
                    for k in kanji_chars:
                        km = kanji_meanings.get(k, 'Meaning not found')
                        kanji_meanings_html += f'''
                        <div class="kanji-in-word">
                            <span class="small-kanji">{k}</span>
                            <span class="kanji-meaning">{km}</span>
                        </div>'''
                else:
                    kanji_meanings_html = '<div class="kanji-in-word">(Fewer than 2 kanji – no breakdown)</div>'
                
                # Vocab card: clickable only if there are details
                clickable_class = 'clickable' if has_kanji_details else ''
                onclick_attr = f'onclick="toggleVocab(this.parentElement)"' if has_kanji_details else ''
                toggle_icon = '<span class="vocab-toggle">▼</span>' if has_kanji_details else ''
                
                html_content += f'''
                        <div class="vocab-card collapsed">
                            <div class="vocab-header {clickable_class}" {onclick_attr}>
                                <div class="vocab-header-left">
                                    <div>
                                        <span class="word-index">#{word_index}</span>
                                        <span class="vocab-expression">{expression}</span>
                                    </div>
                                    <div class="vocab-reading">{reading}</div>
                                    <div class="vocab-meaning">{meaning}</div>
                                </div>
                                {toggle_icon}
                            </div>
                            <div class="vocab-details">
                                {kanji_meanings_html}
                            </div>
                        </div>
'''
            # Close group-content and group-section
            html_content += '''
                    </div>
                </div>
'''
        
        html_content += '''
            </div>
        </div>
'''
    
    # Final HTML and JavaScript
    html_content += '''
        </div>
    </div>
    
    <script>
        function toggleLevel(element) { element.classList.toggle('collapsed'); }
        function toggleGroup(element) { element.classList.toggle('collapsed'); }
        function toggleVocab(card) { card.classList.toggle('collapsed'); }
        
        function expandAllLevelsAndGroups() {
            document.querySelectorAll('.level-section').forEach(l => l.classList.remove('collapsed'));
            document.querySelectorAll('.group-section').forEach(g => g.classList.remove('collapsed'));
        }
        function collapseAllLevelsAndGroups() {
            document.querySelectorAll('.level-section').forEach(l => l.classList.add('collapsed'));
            document.querySelectorAll('.group-section').forEach(g => g.classList.add('collapsed'));
        }
        
        // Search: expand parent groups/levels when match found
        const searchBox = document.getElementById('searchBox');
        searchBox.addEventListener('input', function(e) {
            const term = e.target.value.toLowerCase().trim();
            const vocabCards = document.querySelectorAll('.vocab-card');
            vocabCards.forEach(card => {
                const expression = card.querySelector('.vocab-expression')?.innerText.toLowerCase() || '';
                const reading = card.querySelector('.vocab-reading')?.innerText.toLowerCase() || '';
                const meaning = card.querySelector('.vocab-meaning')?.innerText.toLowerCase() || '';
                const matches = term === '' || expression.includes(term) || reading.includes(term) || meaning.includes(term);
                card.style.display = matches ? '' : 'none';
                if (matches && term !== '') {
                    const parentGroup = card.closest('.group-section');
                    if (parentGroup && parentGroup.classList.contains('collapsed')) parentGroup.classList.remove('collapsed');
                    const parentLevel = card.closest('.level-section');
                    if (parentLevel && parentLevel.classList.contains('collapsed')) parentLevel.classList.remove('collapsed');
                }
            });
            // Hide level sections with no visible cards (only when searching)
            document.querySelectorAll('.level-section').forEach(sec => {
                const visible = sec.querySelectorAll('.vocab-card[style="display: block;"]');
                sec.style.display = (term !== '' && visible.length === 0) ? 'none' : '';
            });
        });
        
        // Initially collapse all groups (already done by 'collapsed' class on group-section)
        // No extra DOMContentLoaded needed – groups are collapsed by default.
    </script>
</body>
</html>
'''
    
    with open('vocab_by_jlpt.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ Created vocab_by_jlpt.html")
    print("   - Grouped by JLPT level (N5–N1) and into collapsible batches of 30 words.")
    print("   - Running index shown per word.")
    print("   - Kanji details only appear for words with ≥2 kanji.")
    print("   - All groups start collapsed. Use Expand All / Collapse All buttons.")

if __name__ == "__main__":
    create_vocab_by_jlpt_html()