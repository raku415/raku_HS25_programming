# quick_test.py - Schneller Test für Unterlagen & Kriterien
import re
import pdfplumber

# Lies das PDF
pdf_path = "Emmenbrücke.pdf"

print("Lese PDF...")
with pdfplumber.open(pdf_path) as pdf:
    txt = "\n".join((p.extract_text() or "") for p in pdf.pages)

print(f"PDF gelesen: {len(txt)} Zeichen\n")

SEC_HEAD = r"(?m)^(?P<num>\d+(?:\.\d+)*)\s+(?P<title>[A-ZÄÖÜa-zäöü].+)$"

def get_section_block(txt: str, title_regex: str):
    """NEUE VERSION: Nimmt die LÄNGSTE Sektion (ignoriert TOC)"""
    secs = list(re.finditer(SEC_HEAD, txt))
    matches = []
    
    for i, m in enumerate(secs):
        num = m.group('num')
        title = m.group('title')
        full_header = f"{num} {title}"
        if re.search(title_regex, full_header, flags=re.I):
            start = m.start()
            end = secs[i+1].start() if i+1 < len(secs) else len(txt)
            content_length = end - start
            matches.append((start, end, content_length, num, title))
    
    # Nimm die LÄNGSTE Sektion (die mit dem echten Inhalt)
    if matches:
        print(f"  Gefunden: {len(matches)} Matches für Pattern '{title_regex}'")
        for start, end, length, num, title in matches:
            print(f"    - {num} {title[:30]}... → {length} Zeichen")
        best = max(matches, key=lambda x: x[2])
        print(f"  → Nehme längste: {best[3]} ({best[2]} Zeichen)")
        return txt[best[0]:best[1]]
    
    return None

print("="*80)
print("TEST 1: Sektion 3.6 (Einzureichende Unterlagen)")
print("="*80)
sec36 = get_section_block(txt, r"^3\.6\b")
if sec36:
    print(f"Sektion 3.6 gefunden! Länge: {len(sec36)} Zeichen")
    print("\nErste 1000 Zeichen:")
    print(sec36[:1000])
else:
    print("Sektion 3.6 NICHT gefunden!")

print("\n" + "="*80)
print("TEST 2: Sektion 3.5 (Alternative)")
print("="*80)
sec35 = get_section_block(txt, r"^3\.5\b")
if sec35:
    print(f"Sektion 3.5 gefunden! Länge: {len(sec35)} Zeichen")
    print("\nErste 800 Zeichen:")
    print(sec35[:800])
else:
    print("Sektion 3.5 NICHT gefunden!")

print("\n" + "="*80)
print("TEST 3: Sektion 4 (Beurteilungskriterien)")
print("="*80)
sec4 = get_section_block(txt, r"^4\b")
if sec4:
    print(f"Sektion 4 gefunden! Länge: {len(sec4)} Zeichen")
    print("\nInhalt:")
    print(sec4[:800])
else:
    print("Sektion 4 NICHT gefunden!")

print("\n" + "="*80)
print("TEST 4: Alle Sektionen anzeigen")
print("="*80)
secs = list(re.finditer(SEC_HEAD, txt))
print(f"Gefundene Sektionen: {len(secs)}\n")
for m in secs[:30]:  # Erste 30
    print(f"  {m.group('num')}: {m.group('title')[:50]}")