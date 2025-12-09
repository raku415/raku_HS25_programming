# quick_test.py - Schneller Test für Abgabetermin
import re

# Dein Text-Snippet
test_text = """
3.7 Abgabetermin und Eingabeort
Planunterlagen und Verfassercouvert 10.12.2015, 16:00h

Eingabeort für sämtliche Unterlagen ist das Sekretariat für den Studienwettbewerb. (consero ag).
"""

print("="*80)
print("TEST 1: Finde Sektion 3.7")
print("="*80)

SEC_HEAD = r"(?m)^(?P<num>\d+(?:\.\d+)*)\s+(?P<title>[A-ZÄÖÜa-zäöü].+)$"
sections = list(re.finditer(SEC_HEAD, test_text))
print(f"Gefundene Sektionen: {len(sections)}")
for m in sections:
    print(f"  - {m.group('num')} {m.group('title')}")

print("\n" + "="*80)
print("TEST 2: Suche nach Verfassercouvert")
print("="*80)

lines = test_text.splitlines()
for i, ln in enumerate(lines, 1):
    if re.search(r"(?i)Verfassercouvert", ln):
        print(f"Zeile {i}: {ln}")
        print(f"  Enthält 'Verfassercouvert': ✓")
        
        # Teste verschiedene Patterns
        patterns = [
            (r"(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4}),\s*(?P<time>\d{1,2}:\d{2})h", "Pattern A: DATE, TIMEh"),
            (r"(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4}),\s*(?P<time>\d{1,2}:\d{2})\s*h", "Pattern B: DATE, TIME h"),
            (r"(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4})[,\s]+(?P<time>\d{1,2}:\d{2})", "Pattern C: flexibel"),
        ]
        
        for pattern, desc in patterns:
            m = re.search(pattern, ln)
            if m:
                print(f"  ✓ {desc} → Datum: {m.group('date')}, Zeit: {m.group('time')}")
            else:
                print(f"  ✗ {desc}")

print("\n" + "="*80)
print("TEST 3: Kompletter Extraktions-Test")
print("="*80)

def get_section_block(txt: str, title_regex: str):
    secs = list(re.finditer(SEC_HEAD, txt))
    print(f"\nget_section_block: Suche nach Pattern '{title_regex}'")
    for i, m in enumerate(secs):
        num = m.group('num')
        title = m.group('title')
        full_header = f"{num} {title}"
        print(f"  Prüfe: '{full_header}'")
        if re.search(title_regex, full_header, flags=re.I):
            print(f"    ✓ MATCH!")
            start = m.start()
            end = secs[i+1].start() if i+1 < len(secs) else len(txt)
            return txt[start:end]
        else:
            print(f"    ✗ kein Match")
    return None

sec37 = get_section_block(test_text, r"^3\.7\b")
if sec37:
    print("Sektion 3.7 gefunden!")
    print(f"Inhalt:\n{sec37}")
else:
    print("Sektion 3.7 NICHT gefunden!")

print("\n" + "="*80)
print("TEST 4: Suche in den Zeilen")
print("="*80)

keywords = [r"\bVerfassercouvert\b", r"\bPlanunterlagen\b", r"\bAbgabetermin\b"]
time_patterns = [
    r"(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4}),\s*(?P<time>\d{1,2}:\d{2})h",
]

if sec37:
    for ln in sec37.splitlines():
        has_keyword = any(re.search(kw, ln, re.I) for kw in keywords)
        if has_keyword:
            print(f"\nZeile mit Keyword: {ln}")
            for pattern in time_patterns:
                m = re.search(pattern, ln)
                if m:
                    print(f"  ✓ Gefunden! Datum: {m.group('date')}, Zeit: {m.group('time')}")
                else:
                    print(f"  ✗ Pattern matched nicht")

print("\n" + "="*80)
print("FERTIG")
print("="*80)