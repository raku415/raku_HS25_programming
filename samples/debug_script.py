# debug_extract.py
import re
import pdfplumber
from pathlib import Path

def debug_abgabetermin(txt: str):
    """Debug: Zeigt alle Zeilen mit 'Abgabe' und Datumsmustern"""
    print("="*80)
    print("DEBUG: ABGABETERMIN")
    print("="*80)
    
    # Suche alle Zeilen mit "Abgabe"
    for i, line in enumerate(txt.splitlines(), 1):
        if re.search(r"(?i)abgabe", line):
            print(f"\nZeile {i}: {line[:150]}")
            # Prüfe auf Datumsmuster
            date_match = re.search(r"\d{1,2}\.\d{1,2}\.\d{2,4}", line)
            time_match = re.search(r"\d{1,2}:\d{2}", line)
            if date_match:
                print(f"  → DATUM gefunden: {date_match.group(0)}")
            if time_match:
                print(f"  → ZEIT gefunden: {time_match.group(0)}")
    
    # Suche speziell Sektion 3.7
    print("\n" + "="*80)
    print("SEKTION 3.7 INHALT:")
    print("="*80)
    sec_match = re.search(r"(?m)^3\.7\s+.+$(?P<content>(?:\n(?!\d+\.).+)*)", txt)
    if sec_match:
        content = sec_match.group(0)
        print(content[:1000])
    else:
        print("Sektion 3.7 NICHT gefunden!")
    
    # Teste verschiedene Regex-Muster
    print("\n" + "="*80)
    print("REGEX PATTERN TESTS:")
    print("="*80)
    
    patterns = [
        (r"(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4}),?\s*(?P<time>\d{1,2}:\d{2})\s*h", "Pattern 1: DATE, TIME h"),
        (r"(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4}),?\s*(?P<time>\d{1,2}:\d{2})h", "Pattern 2: DATE, TIMEh (kein Space)"),
        (r"(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4})[,\s]+(?P<time>\d{1,2}:\d{2})", "Pattern 3: DATE TIME (flexibel)"),
    ]
    
    test_line = "Planunterlagen und Verfassercouvert 10.12.2015, 16:00h"
    print(f"\nTest-Zeile: {test_line}")
    
    for pattern, desc in patterns:
        m = re.search(pattern, test_line)
        if m:
            print(f"✓ {desc}")
            print(f"  Datum: {m.group('date')}, Zeit: {m.group('time')}")
        else:
            print(f"✗ {desc}")

def debug_abgabeort(txt: str):
    """Debug: Zeigt Kontext um Eingabeort/Abgabeort"""
    print("\n" + "="*80)
    print("DEBUG: ABGABEORT")
    print("="*80)
    
    keywords = ["Eingabeort", "Abgabeort", "Sekretariat"]
    
    for keyword in keywords:
        print(f"\n--- Suche nach: {keyword} ---")
        matches = list(re.finditer(rf"(?i){keyword}", txt))
        print(f"Gefunden: {len(matches)} Treffer")
        
        for i, m in enumerate(matches, 1):
            start = max(0, m.start() - 200)
            end = min(len(txt), m.end() + 200)
            context = txt[start:end]
            print(f"\nTreffer {i} (Position {m.start()}):")
            print(context[:400])
            print("-" * 40)

def main():
    # Lies das PDF
    pdf_path = "Emmenbrücke.pdf"
    
    if not Path(pdf_path).exists():
        print(f"FEHLER: {pdf_path} nicht gefunden!")
        print("Bitte Script im gleichen Ordner wie das PDF ausführen.")
        return
    
    print(f"Lese PDF: {pdf_path}")
    txt_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for p in pdf.pages:
            t = p.extract_text(x_tolerance=1, y_tolerance=1) or ""
            if not t.strip():
                t = p.extract_text() or ""
            txt_pages.append(t)
    
    txt = "\n".join(txt_pages)
    print(f"PDF gelesen: {len(txt)} Zeichen")
    
    # Debug Funktionen aufrufen
    debug_abgabetermin(txt)
    debug_abgabeort(txt)
    
    print("\n" + "="*80)
    print("DEBUG ABGESCHLOSSEN")
    print("="*80)

if __name__ == "__main__":
    main()