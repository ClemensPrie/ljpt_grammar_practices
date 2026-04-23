import pandas as pd
import re
import json
from pathlib import Path

def extract_jlpt_level(tags):
    """Extract JLPT level from tags column."""
    if pd.isna(tags) or not isinstance(tags, str):
        return None
    match = re.search(r'JLPT_([Nn][1-5])', tags)
    if match:
        return match.group(1).upper()
    return None

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

def create_kanji_study_html():
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
            print(f"Warning: {filename} not found")
            continue
        df = pd.read_csv(filename)
        df.columns = df.columns.str.lower()
        df['jlpt_level'] = level
        all_vocab.append(df)
    
    if not all_vocab:
        print("Error: No vocabulary files found!")
        return
    
    vocab_df = pd.concat(all_vocab, ignore_index=True)
    # Prefer JLPT from tags if present
    vocab_df['extracted_jlpt'] = vocab_df['tags'].apply(extract_jlpt_level)
    vocab_df['final_jlpt'] = vocab_df['extracted_jlpt'].fillna(vocab_df['jlpt_level'])
    print(f"Loaded {len(vocab_df)} vocabulary entries")
    
    # Load joyo kanji
    joyo_df = pd.read_csv('joyo.csv')
    # Convert grade to string for consistent handling
    joyo_df['grade'] = joyo_df['grade'].astype(str)
    print(f"Loaded {len(joyo_df)} kanji")
    print("Grade distribution:", joyo_df['grade'].value_counts().sort_index().to_dict())
    
    # Build mapping: kanji -> vocab grouped by JLPT level
    kanji_to_vocab = {}
    for _, row in vocab_df.iterrows():
        expression = str(row['expression'])
        kanji_chars = set(re.findall(r'[\u4e00-\u9faf]', expression))
        for kanji in kanji_chars:
            if kanji not in kanji_to_vocab:
                kanji_to_vocab[kanji] = []
            kanji_to_vocab[kanji].append({
                'expression': expression,
                'reading': row.get('reading', ''),
                'meaning': row.get('meaning', ''),
                'jlpt': row['final_jlpt']
            })
    
    # Group vocab by JLPT level for each kanji
    for kanji in kanji_to_vocab:
        grouped = {}
        for v in kanji_to_vocab[kanji]:
            lvl = v['jlpt']
            if lvl not in grouped:
                grouped[lvl] = []
            grouped[lvl].append(v)
        kanji_to_vocab[kanji] = grouped
    
    # Start building HTML
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>JLPT Kanji Study Guide</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f5f5;
            padding: 16px;
            color: #333;
        }
        .container { max-width: 600px; margin: 0 auto; }
        h1 { font-size: 28px; margin-bottom: 8px; color: #1a1a1a; }
        .subtitle { color: #666; margin-bottom: 24px; font-size: 14px; }
        
        .grade-section {
            background: white;
            border-radius: 12px;
            margin-bottom: 16px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .grade-header {
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
        .grade-header.grade-1 { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .grade-header.grade-2 { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
        .grade-header.grade-3 { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
        .grade-header.grade-4 { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
        .grade-header.grade-5 { background: linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%); }
        .grade-header.grade-6 { background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); }
        .grade-header.grade-S { background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); color: #333; }
        .grade-header span:first-child { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
        .grade-badge { background: rgba(255,255,255,0.2); padding: 4px 10px; border-radius: 20px; font-size: 14px; }
        .toggle-icon { font-size: 20px; transition: transform 0.3s; }
        .grade-section.collapsed .toggle-icon { transform: rotate(-90deg); }
        .grade-content { padding: 16px; display: block; }
        .grade-section.collapsed .grade-content { display: none; }
        
        .kanji-card {
            background: #fafafa;
            border-radius: 10px;
            margin-bottom: 12px;
            border: 1px solid #e8e8e8;
            overflow: hidden;
        }
        .kanji-header {
            padding: 16px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: white;
            transition: background 0.2s;
            user-select: none;
        }
        .kanji-header:hover { background: #f5f5f5; }
        .kanji-header-left { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
        .kanji-char { font-size: 36px; font-weight: bold; font-family: "Hiragino Kaku Gothic Pro", "Noto Sans CJK JP", sans-serif; min-width: 60px; }
        .kanji-summary { display: flex; flex-direction: column; gap: 4px; }
        .kanji-meanings { font-size: 14px; color: #666; max-width: 200px; }
        .kanji-badges { display: flex; gap: 8px; font-size: 11px; }
        .badge { background: #e8e8e8; padding: 2px 8px; border-radius: 12px; color: #666; }
        .index-badge { background: #667eea; color: white; padding: 2px 8px; border-radius: 20px; font-size: 11px; margin-left: 8px; }
        .kanji-toggle { font-size: 18px; color: #999; transition: transform 0.3s; }
        .kanji-card.collapsed .kanji-toggle { transform: rotate(-90deg); }
        .kanji-details { padding: 0 16px 16px 16px; display: block; border-top: 1px solid #e8e8e8; background: #fafafa; }
        .kanji-card.collapsed .kanji-details { display: none; }
        
        .jlpt-group {
            margin-top: 12px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background: white;
            overflow: hidden;
        }
        .jlpt-header {
            padding: 10px 12px;
            background: #f0f0f0;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: bold;
            font-size: 13px;
            user-select: none;
        }
        .jlpt-header .jlpt-badge {
            background: #667eea;
            color: white;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 11px;
        }
        .jlpt-toggle { font-size: 14px; transition: transform 0.3s; }
        .jlpt-group.collapsed .jlpt-toggle { transform: rotate(-90deg); }
        .jlpt-content { padding: 8px; display: block; }
        .jlpt-group.collapsed .jlpt-content { display: none; }
        
        .vocab-item {
            background: #f9f9f9;
            border-radius: 8px;
            margin-bottom: 8px;
            overflow: hidden;
        }
        .vocab-header {
            padding: 10px 12px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            user-select: none;
            transition: background 0.2s;
        }
        .vocab-header:hover { background: #eef2ff; }
        .vocab-expression { font-size: 16px; font-weight: 500; }
        .vocab-reading { font-size: 11px; color: #999; margin-top: 2px; }
        .vocab-meaning { font-size: 13px; color: #555; margin-top: 2px; }
        .vocab-toggle { font-size: 14px; color: #999; transition: transform 0.3s; margin-left: 8px; }
        .vocab-item.collapsed .vocab-toggle { transform: rotate(-90deg); }
        .vocab-kanji-meanings {
            padding: 8px 12px;
            background: #fff8e7;
            border-top: 1px solid #eee;
            display: block;
            font-size: 13px;
        }
        .vocab-item.collapsed .vocab-kanji-meanings { display: none; }
        .kanji-in-word {
            margin-bottom: 6px;
            border-bottom: 1px solid #f0e0c0;
            padding-bottom: 6px;
        }
        .kanji-in-word:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
        .small-kanji { font-size: 20px; font-weight: bold; margin-right: 8px; }
        
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
        .no-vocab { padding: 12px; color: #999; font-style: italic; }
        .readings { margin-bottom: 12px; }
        .reading-on, .reading-kun { font-size: 13px; margin-right: 16px; }
        .reading-on { color: #e74c3c; }
        .reading-kun { color: #3498db; }
        
        @media (max-width: 480px) {
            body { padding: 12px; }
            .kanji-char { font-size: 28px; min-width: 50px; }
            .kanji-header-left { gap: 10px; }
            .kanji-meanings { font-size: 12px; max-width: 150px; }
        }
        @media print {
            body { background: white; padding: 0; }
            .grade-header, .kanji-header, .jlpt-header, .vocab-header { cursor: default; break-inside: avoid; }
            .grade-section.collapsed .grade-content, .kanji-card.collapsed .kanji-details, .jlpt-group.collapsed .jlpt-content, .vocab-item.collapsed .vocab-kanji-meanings { display: block; }
            .toggle-icon, .kanji-toggle, .jlpt-toggle, .vocab-toggle, .expand-all-btn, .collapse-all-btn, .search-box, .button-group { display: none; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 Kanji Study Guide</h1>
        <div class="subtitle">Jōyō Kanji with JLPT Vocabulary</div>
        <input type="text" class="search-box" id="searchBox" placeholder="🔍 Search kanji, reading, or meaning...">
        <div class="button-group">
            <button class="expand-all-btn" onclick="expandAllKanji()">📖 Expand All Kanji</button>
            <button class="collapse-all-btn" onclick="collapseAllKanji()">📕 Collapse All Kanji</button>
        </div>
        <div id="gradesContainer">
'''
    
    # Prepare grade order: 1-6 then three S subsections
    # We'll process grades 1-6 normally, then split S kanji into three parts
    grades_primary = ['1', '2', '3', '4', '5', '6']
    running_index = 1
    
    # Process grades 1-6
    for grade in grades_primary:
        grade_kanji = joyo_df[joyo_df['grade'] == grade]
        if len(grade_kanji) == 0:
            continue
        
        grade_name = f"Grade {grade}"
        
        html_content += f'''
        <div class="grade-section" id="grade-{grade}">
            <div class="grade-header grade-{grade}" onclick="toggleGrade(this.parentElement)">
                <span><span class="grade-badge">{grade_name}</span><span>({len(grade_kanji)} kanji)</span></span>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="grade-content">
                <div class="stats">📖 {len(grade_kanji)} kanji</div>
'''
        
        for _, row in grade_kanji.iterrows():
            kanji = row['kanji']
            meanings = str(row['meanings'])[:80] if pd.notna(row['meanings']) else ''
            strokes = row['strokes'] if pd.notna(row['strokes']) else '?'
            on_read = str(row['on']).replace('|', ' · ') if pd.notna(row['on']) else '—'
            kun_read = str(row['kun']).replace('|', ' · ') if pd.notna(row['kun']) else '—'
            
            vocab_by_level = kanji_to_vocab.get(kanji, {})
            
            html_content += f'''
            <div class="kanji-card" data-kanji="{kanji}" data-meanings="{meanings.lower()}" data-readings="{on_read} {kun_read}">
                <div class="kanji-header" onclick="toggleKanji(this.parentElement)">
                    <div class="kanji-header-left">
                        <div class="kanji-char">{kanji}</div>
                        <div class="kanji-summary">
                            <div class="kanji-meanings">{meanings}</div>
                            <div class="kanji-badges"><span class="badge">✍️ {strokes} strokes</span><span class="index-badge">#{running_index}</span></div>
                        </div>
                    </div>
                    <div class="kanji-toggle">▼</div>
                </div>
                <div class="kanji-details">
                    <div class="readings">
                        <span class="reading-on">📖 On: {on_read}</span>
                        <span class="reading-kun">🌿 Kun: {kun_read}</span>
                    </div>
'''
            
            # Add JLPT groups (collapsed by default -> will be handled in JS)
            for level in ['N5', 'N4', 'N3', 'N2', 'N1']:
                if level not in vocab_by_level:
                    continue
                vocab_list = vocab_by_level[level]
                if not vocab_list:
                    continue
                html_content += f'''
                    <div class="jlpt-group">
                        <div class="jlpt-header" onclick="toggleJlptGroup(this.parentElement)">
                            <span class="jlpt-badge">{level}</span>
                            <span class="jlpt-toggle">▼</span>
                        </div>
                        <div class="jlpt-content">
'''
                for v in vocab_list:
                    kanji_in_word = re.findall(r'[\u4e00-\u9faf]', v['expression'])
                    meanings_html = ''
                    for k in kanji_in_word:
                        km = kanji_meanings.get(k, 'Meaning not found')
                        meanings_html += f'<div class="kanji-in-word"><span class="small-kanji">{k}</span> {km}</div>'
                    
                    html_content += f'''
                            <div class="vocab-item">
                                <div class="vocab-header" onclick="toggleVocab(this.parentElement)">
                                    <div>
                                        <div class="vocab-expression">{v['expression']}</div>
                                        <div class="vocab-reading">{v['reading']}</div>
                                        <div class="vocab-meaning">{v['meaning']}</div>
                                    </div>
                                    <span class="vocab-toggle">▼</span>
                                </div>
                                <div class="vocab-kanji-meanings">
                                    {meanings_html if meanings_html else '<div>No kanji in this word</div>'}
                                </div>
                            </div>
'''
                html_content += '''
                        </div>
                    </div>
'''
            
            if not vocab_by_level:
                html_content += '<div class="no-vocab">No vocabulary found</div>'
            
            html_content += '''
                </div>
            </div>
'''
            running_index += 1
        
        html_content += '''
            </div>
        </div>
'''
    
    # Process S grade (secondary school) – split into three subsections
    s_df = joyo_df[joyo_df['grade'] == 'S']
    if len(s_df) > 0:
        # Split into three parts
        part1 = s_df.iloc[:370]
        part2 = s_df.iloc[370:740]
        part3 = s_df.iloc[740:]
        
        sections = [
            (part1, "Secondary School (1–370)", "S1"),
            (part2, "Secondary School (371–740)", "S2"),
            (part3, f"Secondary School (741–{len(s_df)})", "S3")
        ]
        
        for part_df, display_name, section_id in sections:
            if len(part_df) == 0:
                continue
            html_content += f'''
        <div class="grade-section" id="grade-{section_id}">
            <div class="grade-header grade-S" onclick="toggleGrade(this.parentElement)">
                <span><span class="grade-badge">{display_name}</span><span>({len(part_df)} kanji)</span></span>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="grade-content">
                <div class="stats">📖 {len(part_df)} kanji</div>
'''
            for _, row in part_df.iterrows():
                kanji = row['kanji']
                meanings = str(row['meanings'])[:80] if pd.notna(row['meanings']) else ''
                strokes = row['strokes'] if pd.notna(row['strokes']) else '?'
                on_read = str(row['on']).replace('|', ' · ') if pd.notna(row['on']) else '—'
                kun_read = str(row['kun']).replace('|', ' · ') if pd.notna(row['kun']) else '—'
                
                vocab_by_level = kanji_to_vocab.get(kanji, {})
                
                html_content += f'''
            <div class="kanji-card" data-kanji="{kanji}" data-meanings="{meanings.lower()}" data-readings="{on_read} {kun_read}">
                <div class="kanji-header" onclick="toggleKanji(this.parentElement)">
                    <div class="kanji-header-left">
                        <div class="kanji-char">{kanji}</div>
                        <div class="kanji-summary">
                            <div class="kanji-meanings">{meanings}</div>
                            <div class="kanji-badges"><span class="badge">✍️ {strokes} strokes</span><span class="index-badge">#{running_index}</span></div>
                        </div>
                    </div>
                    <div class="kanji-toggle">▼</div>
                </div>
                <div class="kanji-details">
                    <div class="readings">
                        <span class="reading-on">📖 On: {on_read}</span>
                        <span class="reading-kun">🌿 Kun: {kun_read}</span>
                    </div>
'''
                for level in ['N5', 'N4', 'N3', 'N2', 'N1']:
                    if level not in vocab_by_level:
                        continue
                    vocab_list = vocab_by_level[level]
                    if not vocab_list:
                        continue
                    html_content += f'''
                    <div class="jlpt-group">
                        <div class="jlpt-header" onclick="toggleJlptGroup(this.parentElement)">
                            <span class="jlpt-badge">{level}</span>
                            <span class="jlpt-toggle">▼</span>
                        </div>
                        <div class="jlpt-content">
'''
                    for v in vocab_list:
                        kanji_in_word = re.findall(r'[\u4e00-\u9faf]', v['expression'])
                        meanings_html = ''
                        for k in kanji_in_word:
                            km = kanji_meanings.get(k, 'Meaning not found')
                            meanings_html += f'<div class="kanji-in-word"><span class="small-kanji">{k}</span> {km}</div>'
                        html_content += f'''
                            <div class="vocab-item">
                                <div class="vocab-header" onclick="toggleVocab(this.parentElement)">
                                    <div>
                                        <div class="vocab-expression">{v['expression']}</div>
                                        <div class="vocab-reading">{v['reading']}</div>
                                        <div class="vocab-meaning">{v['meaning']}</div>
                                    </div>
                                    <span class="vocab-toggle">▼</span>
                                </div>
                                <div class="vocab-kanji-meanings">
                                    {meanings_html if meanings_html else '<div>No kanji in this word</div>'}
                                </div>
                            </div>
'''
                    html_content += '''
                        </div>
                    </div>
'''
                if not vocab_by_level:
                    html_content += '<div class="no-vocab">No vocabulary found</div>'
                html_content += '''
                </div>
            </div>
'''
                running_index += 1
            html_content += '''
            </div>
        </div>
'''
    
    html_content += '''
        </div>
    </div>
    
    <script>
        function toggleGrade(element) { element.classList.toggle('collapsed'); }
        function toggleKanji(element) { element.classList.toggle('collapsed'); }
        function toggleJlptGroup(element) { element.classList.toggle('collapsed'); }
        function toggleVocab(element) { element.classList.toggle('collapsed'); }
        
        function expandAllKanji() {
            document.querySelectorAll('.kanji-card').forEach(c => c.classList.remove('collapsed'));
        }
        function collapseAllKanji() {
            document.querySelectorAll('.kanji-card').forEach(c => c.classList.add('collapsed'));
        }
        
        const searchBox = document.getElementById('searchBox');
        searchBox.addEventListener('input', function(e) {
            const term = e.target.value.toLowerCase().trim();
            const cards = document.querySelectorAll('.kanji-card');
            cards.forEach(card => {
                const kanji = card.getAttribute('data-kanji') || '';
                const meanings = card.getAttribute('data-meanings') || '';
                const readings = card.getAttribute('data-readings') || '';
                if (term === '') {
                    card.style.display = 'block';
                } else if (kanji.includes(term) || meanings.includes(term) || readings.includes(term)) {
                    card.style.display = 'block';
                    card.classList.remove('collapsed');
                    const gradeSec = card.closest('.grade-section');
                    if (gradeSec) gradeSec.classList.remove('collapsed');
                } else {
                    card.style.display = 'none';
                }
            });
            document.querySelectorAll('.grade-section').forEach(sec => {
                const visible = sec.querySelectorAll('.kanji-card[style="display: block;"]');
                sec.style.display = (term !== '' && visible.length === 0) ? 'none' : 'block';
            });
        });
        
        // Initialize: all kanji collapsed, JLPT groups collapsed, vocab items collapsed
        document.addEventListener('DOMContentLoaded', function() {
            collapseAllKanji();
            // Make all JLPT groups collapsed by default
            document.querySelectorAll('.jlpt-group').forEach(g => g.classList.add('collapsed'));
            // All vocab items start collapsed
            document.querySelectorAll('.vocab-item').forEach(v => v.classList.add('collapsed'));
        });
    </script>
</body>
</html>
'''
    
    with open('kanji_study_guide.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ Created kanji_study_guide.html")
    print("   All grades (1-6) and three S subsections appear.")
    print("   JLPT sections are collapsed by default.")
    print("   Each kanji has a running index.")
    print("   Click any vocabulary word to expand and see meanings of its kanji.")

if __name__ == "__main__":
    create_kanji_study_html()