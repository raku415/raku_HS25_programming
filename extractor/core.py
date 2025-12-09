# extractor/core.py
import re
import dateparser


# -------- Regex-Bausteine --------
SEC_HEAD = r"(?m)^(?P<num>\d+(?:\.\d+)*)\s+(?P<title>[A-ZÄÖÜa-zäöü].+)$"
DATE_TIME = r"(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4})(?:,\s*(?P<time>\d{1,2}:\d{2})\s*h?)?"
ABGABE = r"(?i)Abgabetermin[^\n]*\n?(?P<line>.+)"
BESICHT = r"(?i)Besichtigung.*?am\s*(?P<date>\d{1,2}\.\d{1,2}\.\d{4}).*?\bum\b\s*(?P<time>\d{1,2}:\d{2})\s*Uhr(?P<tail>.*)"
EMAIL = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
PHONE = r"(?:\+?\d[\d\s]{6,})"

BULLET = r"(?:•|\-|–|\*)"

def norm_date(d, t=None):
    if not d: 
        return None, None
    dt = dateparser.parse(f"{d} {t or ''}", languages=['de'])
    if not dt: 
        return None, None
    return dt.date().isoformat(), dt.strftime("%H:%M") if t else None

def _collect_bullets(block: str):
    lines = []
    for ln in block.splitlines():
        if re.match(rf"\s*{BULLET}\s+", ln):
            lines.append(re.sub(rf"^\s*{BULLET}\s+", "", ln).strip())
    return [x for x in lines if x]



# --- Einzel-Extractor ---

def get_section_block(txt: str, title_regex: str) -> str | None:
    """
    Liefert den Textblock einer Sektion, deren Nummer oder Titel auf title_regex matched.
    Nutzt das bestehende Überschriftenmuster SEC_HEAD.
    WICHTIG: Nimmt die LETZTE Sektion mit dieser Nummer (ignoriert Inhaltsverzeichnis)
    """
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
    
    # Nimm die LÄNGSTE Sektion (die mit dem echten Inhalt, nicht das TOC)
    if matches:
        best = max(matches, key=lambda x: x[2])
        return txt[best[0]:best[1]]
    
    return None

def strip_toc(txt: str) -> str:
    """
    Entfernt das Inhaltsverzeichnis grob: ab 'Inhaltsverzeichnis' bis zur ersten
    Hauptüberschrift '1 ' oder '1.' o. ä. Falls nicht vorhanden: gibt Original zurück.
    """
    import re
    m = re.search(r"(?im)^inhaltsverzeichnis\s*$", txt)
    if not m:
        return txt
    # ab TOC-Start suchen wir die erste große Ziffernüberschrift
    m2 = re.search(r"(?m)^(?:1[\.\s]+[A-ZÄÖÜa-zäöü]|1\s+[A-ZÄÖÜa-zäöü])", txt[m.end():])
    if not m2:
        return txt
    cut = m.end() + m2.start()
    return txt[cut:]

def extract_sections(txt):
    sections = []
    for m in re.finditer(SEC_HEAD, txt):
        sections.append((m.start(), m.group('num'), m.group('title')))
    blocks = []
    for i,(pos,num,title) in enumerate(sections):
        end = sections[i+1][0] if i+1 < len(sections) else len(txt)
        blocks.append({"nr": num, "titel": title.strip(), "text": txt[pos:end].strip()})
    return blocks

def extract_abgabetermin(txt):
    """
    OPTIMIERTE VERSION für Emmenbrücke PDF:
    Sucht nach "Planunterlagen und Verfassercouvert" mit Datum/Zeit
    Format: "10.12.2015, 16:00h"
    """
    # Arbeite mit dem Originaltext (strip_toc entfernt manchmal zu viel)
    txt_no_toc = txt
    
    # BLACKLIST für Begriffe, die NICHT der Abgabetermin sind
    blacklist_patterns = [
        r"(?i)\bProgrammgenehmigung\b",
        r"(?i)\bBeschluss\b",
        r"(?i)\bProtokoll\b",
        r"(?i)\bBaustart\b",
        r"(?i)\bBauvollendung\b",
        r"(?i)\bBewilligung\b",
        r"(?i)\bVersand\s+Programm\b",
        r"(?i)\bBegehung\b",
        r"(?i)\bFragenstellung\b",
        r"(?i)\bFragenbeantwortung\b",
        r"(?i)\bVorprüfung\b",
        r"(?i)\bPräsentation\b",
        r"(?i)\bAuslobung\b",
    ]
    
    def is_blacklisted(text):
        """Prüft ob Text einen Blacklist-Begriff enthält"""
        for pattern in blacklist_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    candidates = []
    
    # STRATEGIE 0: Direkte Suche nach dem exakten Pattern (höchste Priorität!)
    # Suche nach "Planunterlagen und Verfassercouvert DD.MM.YYYY, HH:MMh"
    direct_pattern = r"(?i)Planunterlagen\s+und\s+Verfassercouvert\s+(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4}),\s*(?P<time>\d{1,2}:\d{2})h"
    for m in re.finditer(direct_pattern, txt_no_toc):
        line = txt_no_toc[max(0, m.start()-50):min(len(txt_no_toc), m.end()+50)].splitlines()
        for ln in line:
            if "Planunterlagen" in ln:
                candidates.append(("direct_pattern", ln.strip(), m.group('date'), m.group('time'), 150))
                break
    
    # STRATEGIE 1: Suche in Sektion 3.7 oder 3.8 (höchste Priorität)
    # Achte auf "Abgabetermin", "Verfassercouvert", "Planunterlagen"
    for section_num in ["3.8", "3.7"]:  # 3.8 zuerst, da "Abgabetermin und Eingabeort" dort sein könnte
        # Suche nach exakter Nummer (z.B. "3.7")
        sec = get_section_block(txt_no_toc, rf"^{re.escape(section_num)}\b")
        if not sec:
            continue
        
        # Debug: Prüfe ob relevante Keywords vorhanden sind
        if not re.search(r"(?i)(Abgabetermin|Verfassercouvert|Planunterlagen|Eingabeort)", sec):
            continue
        
        # WICHTIG: Auch nach "Verfassercouvert" und "Planunterlagen" suchen!
        keywords = [
            r"\bAbgabetermin\b",
            r"\bEingabetermin\b",
            r"\bVerfassercouvert\b",
            r"\bPlanunterlagen\b",
        ]
        
        # Pattern für Datum + Uhrzeit (verschiedene Varianten)
        # WICHTIG: Komma ist optional, Leerzeichen vor "h" ist optional
        time_patterns = [
            r"(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4}),\s*(?P<time>\d{1,2}:\d{2})h",  # 10.12.2015, 16:00h
            r"(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4}),\s*(?P<time>\d{1,2}:\d{2})\s*h",  # mit Space vor h
            r"(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4})\s+(?P<time>\d{1,2}:\d{2})\s*h",  # ohne Komma
            r"(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4}),?\s*(?P<time>\d{1,2}:\d{2})",  # generisch
        ]
        
        for ln in sec.splitlines():
            # WICHTIG: Überspringe die Überschriftszeile selbst (z.B. "3.7 Abgabetermin und Eingabeort")
            if re.match(r"^\d+\.\d+\s+", ln):
                continue
            
            # Prüfe ob Zeile eines der Keywords enthält
            has_keyword = any(re.search(kw, ln, re.I) for kw in keywords)
            if not has_keyword:
                continue
            
            if is_blacklisted(ln):
                continue
            
            # Versuche Datum/Zeit zu finden
            for pattern in time_patterns:
                m = re.search(pattern, ln)
                if m:
                    candidates.append(("section_exact", ln.strip(), m.group('date'), m.group('time'), 100))
                    break
        
        # Falls nicht in derselben Zeile: schaue in den nächsten Zeilen
        lines = sec.splitlines()
        for i, ln in enumerate(lines):
            has_keyword = any(re.search(kw, ln, re.I) for kw in keywords)
            if not has_keyword:
                continue
            
            if is_blacklisted(ln):
                continue
            
            # Schaue in den nächsten 3 Zeilen
            for j in range(i+1, min(i+4, len(lines))):
                next_line = lines[j]
                if is_blacklisted(next_line):
                    continue
                
                for pattern in time_patterns:
                    m = re.search(pattern, next_line)
                    if m:
                        raw = f"{ln.strip()} {next_line.strip()}"
                        candidates.append(("section_follow", raw, m.group('date'), m.group('time'), 95))
                        break
    
    # STRATEGIE 2: Suche in Kapitel 3 (Termine) generell
    if not candidates:
        m3 = re.search(r"(?is)\n3\.\s.*?(?P<blk>(?:\n.+?)+?)(?:\n\d+\.\s|$)", txt_no_toc)
        if m3:
            blk = m3.group('blk')
            for ln in blk.splitlines():
                if re.search(r"(?i)\b(Abgabetermin|Eingabetermin|Verfassercouvert|Planunterlagen)\b", ln):
                    if is_blacklisted(ln):
                        continue
                    m = re.search(r"(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4}),?\s*(?P<time>\d{1,2}:\d{2})", ln)
                    if m:
                        candidates.append(("kap3", ln.strip(), m.group('date'), m.group('time'), 50))
    
    if not candidates:
        return {}
    
    # Wähle Kandidaten mit höchster Priorität
    best = max(candidates, key=lambda x: x[4])
    iso, time = norm_date(best[2], best[3])
    
    return {
        "raw": best[1], 
        "iso": iso, 
        "time": time,
        "source": best[0]
    }


def extract_abgabeort(txt: str):
    """
    OPTIMIERTE VERSION für Emmenbrücke PDF:
    Sucht "Eingabeort für sämtliche Unterlagen ist das Sekretariat..."
    """
    txt_no_toc = strip_toc(txt)
    
    # Priorität 1: Direkte Suche nach dem Satzmuster
    pattern = r"(?i)Eingabeort\s+für\s+sämtliche\s+Unterlagen\s+ist\s+(?P<ort>[^.]+)"
    m = re.search(pattern, txt_no_toc)
    
    if m:
        ort_text = m.group('ort').strip()
        # Bereinige den Text
        ort_text = re.sub(r'\s+', ' ', ort_text)
        
        lines = [ort_text]
        
        # Suche nach ergänzenden Infos in der Nähe (im gleichen Abschnitt)
        start = max(0, m.start() - 500)
        end = min(len(txt_no_toc), m.end() + 500)
        context = txt_no_toc[start:end]
        
        # Suche nach spezifischen Infos
        patterns_to_find = [
            (r"consero\s+ag", "consero ag"),
            (r"Park\s+Höchi\s+Allee\s+\d+", None),
            (r"CH\s*\d{4}\s+\w+", None),
            (r"\d{4}\s+\w+", None),  # PLZ + Ort
        ]
        
        for pat, default in patterns_to_find:
            match = re.search(pat, context, re.I)
            if match:
                found_text = match.group(0).strip()
                if found_text not in ort_text and found_text not in '\n'.join(lines):
                    lines.append(found_text)
        
        # Suche auch nach E-Mail und Telefon im Sekretariat-Abschnitt
        sec_sekretariat = get_section_block(txt_no_toc, r"Leitung.*Sekretariat")
        if sec_sekretariat:
            email_match = re.search(EMAIL, sec_sekretariat)
            if email_match:
                lines.append(email_match.group(0))
            
            phone_match = re.search(r"t\s+[\+\d\s]+", sec_sekretariat)
            if phone_match:
                lines.append(phone_match.group(0).strip())
        
        if lines:
            return {
                "raw_block": "\n".join(lines[:6]),
                "lines": lines[:6],
                "source": "direct_match"
            }
    
    # Fallback: Suche in Sektion 3.7 oder 3.8
    for section_num in ["3.7", "3.8"]:
        sec = get_section_block(txt_no_toc, rf"^{re.escape(section_num)}\b")
        if not sec:
            continue
        
        # Suche nach "Eingabeort" oder "Sekretariat"
        if re.search(r"(?i)(Eingabeort|Sekretariat)", sec):
            lines = []
            
            for ln in sec.splitlines():
                s = ln.strip()
                if not s:
                    continue
                
                # Sammle relevante Zeilen
                if re.search(r"(?i)(Eingabeort|Sekretariat|consero)", s):
                    lines.append(s)
                elif re.search(r"\b\d{4}\s+[A-ZÄÖÜa-zäöü]", s):  # PLZ
                    lines.append(s)
                elif re.search(r"(?i)(Park|Allee|Strasse)", s):
                    lines.append(s)
            
            # Deduplizieren
            seen = set()
            unique = []
            for line in lines:
                if line not in seen:
                    seen.add(line)
                    unique.append(line)
            
            if unique:
                return {
                    "raw_block": "\n".join(unique[:6]),
                    "lines": unique[:6],
                    "source": f"section_{section_num}"
                }
    
    return {}


def extract_unterlagen(txt: str):
    """
    ERWEITERTE VERSION:
    Extrahiert Unterlagen mit Titel und Beschreibung
    Format: [{titel: "Situation", beschreibung: "1:500 als Erdgeschoss..."}, ...]
    """
    # Strategie 1: Suche nach Sektion die "Einzureichende" im Titel hat
    sec = get_section_block(txt, r"Einzureichende.*Unterlagen")
    
    if not sec:
        # Strategie 2: Suche in 3.5 oder 3.6
        for section_num in ["3.6", "3.5"]:
            sec = get_section_block(txt, rf"^{section_num}\b")
            if sec and len(sec) > 100:
                break
    
    if not sec or len(sec) < 50:
        return []
    
    unterlagen = []
    lines = sec.splitlines()
    
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        
        # Überspringe Überschriften und leere Zeilen
        if re.match(r"^\d+\.\d+\s+", ln) or not ln:
            i += 1
            continue
        
        # Erkenne Bullet-Point mit Titel (z.B. "• Situation" oder "• Grundrisse")
        bullet_match = re.match(r"^[•\-]\s+(?P<titel>[A-Za-zÄÖÜäöü\s]+)\s*(?P<rest>.*)$", ln)
        
        if bullet_match:
            titel = bullet_match.group('titel').strip()
            rest = bullet_match.group('rest').strip()
            
            # Sammle Beschreibungstext (kann mehrzeilig sein)
            beschreibung_parts = [rest] if rest else []
            
            # Schaue in die nächsten Zeilen für weiteren Text
            j = i + 1
            while j < len(lines):
                next_ln = lines[j].strip()
                
                # Stop bei nächstem Bullet oder Überschrift
                if re.match(r"^[•\-]\s+", next_ln) or re.match(r"^\d+\.\d+\s+", next_ln):
                    break
                
                # Stop bei bestimmten Keywords (neue Sektion)
                if re.match(r"^(Um\s+eine|Brun\s+Emmenweid)", next_ln):
                    break
                
                # Füge Text hinzu
                if next_ln:
                    beschreibung_parts.append(next_ln)
                
                j += 1
            
            # Erstelle Unterlage-Objekt
            beschreibung = " ".join(beschreibung_parts).strip()
            
            unterlagen.append({
                "titel": titel,
                "beschreibung": beschreibung if beschreibung else None
            })
            
            # Springe zu nächster relevanter Zeile
            i = j
        else:
            i += 1
    
    return unterlagen[:25]  # Max 25 Items

def extract_besichtigung(txt):
    m = re.search(BESICHT, txt, flags=re.DOTALL)
    if not m: 
        return {}
    iso, time = norm_date(m.group('date'), m.group('time'))
    tail = m.group('tail') or ""
    treff = None
    mm = re.search(r"(?i)Treffpunkt(?:\s+ist)?\s+(?P<p>.+?)(?:\.|\n)", tail)
    if mm:
        treff = mm.group('p').strip()
    return {"raw": m.group(0).splitlines()[0].strip(), "iso": iso, "time": time, "treffpunkt": treff}

def extract_contacts(txt):
    contacts = []
    for em in re.finditer(EMAIL, txt):
        span = (max(0, em.start()-160), min(len(txt), em.end()+160))
        window = txt[span[0]:span[1]]
        tel = re.search(PHONE, window)
        name = None
        lines = window.splitlines()
        for i,ln in enumerate(lines):
            if em.group(0) in ln and i>0:
                prev = lines[i-1].strip()
                if 2 <= len(prev.split()) <= 8:
                    name = prev
        contacts.append({
            "name": name,
            "telefon": tel.group(0).strip() if tel else None,
            "email": em.group(0)
        })
    # dedupe per email
    seen = set(); uniq=[]
    for c in contacts:
        if c["email"] in seen: 
            continue
        seen.add(c["email"]); uniq.append(c)
    return uniq

def extract_kriterien(txt):
    """
    ÜBERARBEITETE VERSION:
    Sucht Überschrift "Beurteilungskriterien" in Sektion 4 und sammelt Bullet-Zeilen
    Wichtig: Unterscheidet zwischen Kriterien und anderen Listen
    """
    # Suche in Sektion 4 (nimmt die längste = die mit Inhalt)
    sec = get_section_block(txt, r"^4\b")
    
    if not sec or len(sec) < 50:
        return []
    
    kriterien = []
    
    for ln in sec.splitlines():
        s = ln.strip()
        
        # Überspringe Überschriften
        if re.match(r"^\d+\.?\d*\s+", s):
            continue
        
        # Stoppe bei bestimmten Keywords
        if re.search(r"(?i)(Reihenfolge|Gewichtung|Massgebend)", s):
            break
        
        # Sammle Bullet-Points
        if re.match(r"^[•\-]\s+", s):
            item = re.sub(r"^[•\-]\s+", "", s).strip()
            # Filter: Keine Namen von Architekten/Personen, min. 15 Zeichen
            if len(item) > 15 and not re.search(r"(Zürich|Luzern|Emmen|Weggis|Brun|Heierle)", item, re.I):
                kriterien.append(item)
    
    return kriterien

def extract_teilnehmende(txt):
    # sucht „Teilnehmende … zugelassen:" bis zur nächsten nummerierten Überschrift
    m = re.search(r"(?is)Teilnehmende.*?zugelassen:\s*(?P<blk>(?:\n|.)*?)(?:\n\s*\d+\.\d+|\Z)", txt)
    if not m: 
        return []
    blk = m.group('blk')
    names = [re.sub(r"^[•\-\s]+","",ln).strip()
             for ln in blk.splitlines() if ln.strip()]
    return [n for n in names if any(c.isalpha() for c in n)]

# --- Hauptfunktion ---
def parse_text(txt: str) -> dict:
    data = {
        "abgabetermin": extract_abgabetermin(txt),
        "besichtigung": extract_besichtigung(txt),
        "kontakte": extract_contacts(txt),
        "abgabeort": extract_abgabeort(txt),
        "einzureichende_unterlagen": extract_unterlagen(txt),
        "beurteilungskriterien": extract_kriterien(txt),
        "teilnehmende": extract_teilnehmende(txt),
        "sektionen": extract_sections(txt),
        "meta": {"length": len(txt)}
    }
    return data