# extractor/core.py
import re
import dateparser

SEC_HEAD = r"(?m)^(?P<num>\d+(?:\.\d+)*)\s+(?P<title>[A-ZÄÖÜa-zäöü].+)$"
DATE_TIME = r"(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4})(?:,?\s*(?P<time>\d{1,2}:\d{2})\s*h?)?"
BESICHT = r"(?i)Besichtigung.*?am\s*(?P<date>\d{1,2}\.\d{1,2}\.\d{4}).*?\bum\b\s*(?P<time>\d{1,2}:\d{2})\s*Uhr(?P<tail>.*)"
EMAIL = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
BULLET = r"(?:•|\-|–|\*)"

def norm_date(d, t=None):
    if not d: 
        return None, None
    dt = dateparser.parse(f"{d} {t or ''}", languages=['de'])
    if not dt: 
        return None, None
    return dt.date().isoformat(), dt.strftime("%H:%M") if t else None

def get_section_block(txt: str, title_regex: str):
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
            matches.append((start, end, content_length))
    if matches:
        best = max(matches, key=lambda x: x[2])
        return txt[best[0]:best[1]]
    return None

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
    candidates = []
    direct_pattern = r"(?i)Planunterlagen\s+und\s+Verfassercouvert\s+(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4}),\s*(?P<time>\d{1,2}:\d{2})h"
    for m in re.finditer(direct_pattern, txt):
        line_start = max(0, m.start()-50)
        line_end = min(len(txt), m.end()+50)
        line_text = txt[line_start:line_end].splitlines()
        for ln in line_text:
            if "Planunterlagen" in ln:
                candidates.append((ln.strip(), m.group('date'), m.group('time'), 150))
                break
    
    if not candidates:
        return {}
    
    best = max(candidates, key=lambda x: x[3])
    iso, time = norm_date(best[1], best[2])
    return {"raw": best[0], "iso": iso, "time": time, "source": "direct_pattern"}

def extract_abgabeort(txt: str):
    pattern = r"(?i)Eingabeort\s+für\s+sämtliche\s+Unterlagen\s+ist\s+(?P<ort>[^.]+)"
    m = re.search(pattern, txt)
    if m:
        ort_text = m.group('ort').strip()
        ort_text = re.sub(r'\s+', ' ', ort_text)
        lines = [ort_text]
        
        start = max(0, m.start() - 500)
        end = min(len(txt), m.end() + 500)
        context = txt[start:end]
        
        if re.search(r"consero\s+ag", context, re.I):
            lines.append("consero ag")
        if re.search(r"Park\s+Höchi\s+Allee\s+\d+", context, re.I):
            match_addr = re.search(r"Park\s+Höchi\s+Allee\s+\d+", context, re.I)
            if match_addr:
                lines.append(match_addr.group(0).strip())
        
        if lines:
            return {"raw_block": "\n".join(lines[:6]), "lines": lines[:6], "source": "direct_match"}
    return {}

def extract_unterlagen(txt: str):
    sec = get_section_block(txt, r"Einzureichende.*Unterlagen")
    if not sec:
        for section_num in ["3.6", "3.5"]:
            sec = get_section_block(txt, rf"^{section_num}\b")
            if sec and len(sec) > 100:
                break
    
    if not sec or len(sec) < 50:
        return []
    
    unterlagen = []
    einleitung = None  # Für Fließtext am Anfang
    lines = sec.splitlines()
    i = 0
    
    while i < len(lines):
        ln = lines[i].strip()
        if re.match(r"^\d+\.\d+\s+", ln) or not ln:
            i += 1
            continue
        
        # Erkenne Bullet-Point
        bullet_match = re.match(r"^[•\-]\s+(?P<full>.+)$", ln)
        
        if bullet_match:
            full_text = bullet_match.group('full').strip()
            
            # Spezialfall: Bullet startet mit Zahl (z.B. "1 Satz Pläne")
            number_start = re.match(r"^(\d+)\s+(.+)$", full_text)
            if number_start:
                full_text = number_start.group(2)  # Entferne die führende Zahl
            
            titel = None
            rest = None
            
            # SPEZIALFALL: Erster Bullet-Point ist sehr lang und enthält Einleitungstext
            # z.B. "1 Satz Pläne, ungefalten... Die Grundrisse sind... Es werden keine Begrenzungen..."
            # Wenn er "Es werden" oder "Um eine" enthält = Einleitung
            if i == 0 or (i < 3 and not unterlagen):  # Nur in den ersten Zeilen prüfen
                if re.search(r'(Es werden|Um eine|Sämtliche.*sind|Zu feine)', full_text):
                    # Das ist Einleitungstext - alles sammeln
                    beschreibung_parts = [full_text]
                    j = i + 1
                    while j < len(lines):
                        next_ln = lines[j].strip()
                        # Stoppe beim nächsten Bullet
                        if re.match(r"^[•\-]\s+", next_ln):
                            break
                        if next_ln and not re.match(r"^\d+\.\d+\s+", next_ln):
                            beschreibung_parts.append(next_ln)
                        j += 1
                    
                    einleitung = " ".join(beschreibung_parts).strip()
                    i = j
                    continue
            
            # Pattern 1: "Verkleinerungen auf A4" + Rest
            if full_text.startswith("Verkleinerungen"):
                parts = full_text.split(" für ", 1)
                if len(parts) == 2:
                    titel = parts[0].strip()
                    rest = "für " + parts[1].strip()
                else:
                    titel = full_text
            
            # Pattern 2: Bekannte Titel-Keywords
            elif not titel:
                known_titles = [
                    (r"^(Verkleinerungen auf A4.*)$", "no_detail"),  # Ganzer Text, kein Dropdown
                    (r"^(Satz Pläne.*)$", "no_detail"),  # Ganzer Text als Titel, KEIN Dropdown
                    (r"^(Situation)\s+(.+)$", "has_detail"),
                    (r"^(Grundrisse)\s+(.+)$", "has_detail"),
                    (r"^(Schnitte)\s+(.+)$", "has_detail"),
                    (r"^(Fassaden)\s+(.+)$", "has_detail"),
                    (r"^(Statik)\s+(.+)$", "has_detail"),
                    (r"^(Haustechnik)\s+(.+)$", "has_detail"),
                    (r"^(Visualisierungen)\s+(.+)$", "has_detail"),
                    (r"^(Modell)\s+(.+)$", "has_detail"),
                    (r"^(Honorarofferte)\s+(.+)$", "has_detail"),
                    (r"^(Berechnungen)\s+(.+)$", "has_detail"),
                    (r"^(Verfassercouvert)\s+(.+)$", "has_detail"),
                    (r"^(Ertragsspiegel)\s+(.+)$", "has_detail"),
                ]
                
                for pattern, detail_type in known_titles:
                    m = re.match(pattern, full_text, re.I)
                    if m:
                        if detail_type == "no_detail":
                            titel = m.group(1)
                            rest = None
                        else:
                            titel = m.group(1)
                            rest = m.group(2) if len(m.groups()) > 1 and m.group(2) else None
                        break
            
            # Pattern 3: Langer Fließtext ohne klaren Titel (z.B. Einleitung)
            # Wenn Text > 100 Zeichen und kein Doppelpunkt/Komma in ersten 30 Zeichen
            if not titel and len(full_text) > 100:
                first_part = full_text[:30]
                if ':' not in first_part and ',' not in first_part:
                    # Das ist wahrscheinlich Einleitungstext
                    beschreibung_parts = [full_text]
                    j = i + 1
                    while j < len(lines):
                        next_ln = lines[j].strip()
                        if re.match(r"^[•\-]\s+", next_ln) or re.match(r"^\d+\.\d+\s+", next_ln):
                            break
                        if next_ln:
                            beschreibung_parts.append(next_ln)
                        j += 1
                    
                    einleitung = " ".join(beschreibung_parts).strip()
                    i = j
                    continue
            
            # Fallback: Nimm ersten Teil als Titel
            if not titel:
                words = full_text.split()
                if len(words) <= 4:
                    titel = full_text
                else:
                    for word_count in [1, 2, 3]:
                        potential_titel = " ".join(words[:word_count])
                        potential_rest = " ".join(words[word_count:])
                        if potential_rest and (potential_rest[0].isupper() or potential_rest[0].isdigit()):
                            titel = potential_titel
                            rest = potential_rest
                            break
                    
                    if not titel:
                        titel = " ".join(words[:2])
                        rest = " ".join(words[2:]) if len(words) > 2 else None
            
            # Sammle weitere Beschreibungszeilen
            beschreibung_parts = [rest] if rest else []
            
            j = i + 1
            while j < len(lines):
                next_ln = lines[j].strip()
                if re.match(r"^[•\-]\s+", next_ln) or re.match(r"^\d+\.\d+\s+", next_ln):
                    break
                if re.match(r"^(Um\s+eine|Brun\s+Emmenweid)", next_ln):
                    break
                if next_ln:
                    beschreibung_parts.append(next_ln)
                j += 1
            
            beschreibung = " ".join(beschreibung_parts).strip()
            unterlagen.append({
                "titel": titel, 
                "beschreibung": beschreibung if beschreibung else None
            })
            i = j
        else:
            i += 1
    
    # Füge Einleitung am Anfang hinzu (falls vorhanden)
    result = []
    if einleitung:
        result.append({
            "titel": None,
            "beschreibung": einleitung,
            "typ": "einleitung"
        })
    result.extend(unterlagen[:25])
    return result

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
    seen_emails = set()
    EMAIL_CLEAN = r"(?<![a-zA-Z0-9])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![a-zA-Z0-9])"
    PHONE_PATTERN = r"(?:t\s+)?(\+?\d{1,3}[\s\-]?\d{1,3}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2})"
    
    section_patterns = [
        r"(?i)Bauherrenvertretung.*?(?=\n\d+\.\d+|\Z)",
        r"(?i)Leitung\s+und\s+Sekretariat.*?(?=\n\d+\.|\Z)",
    ]
    
    for pattern in section_patterns:
        matches = re.finditer(pattern, txt, re.DOTALL)
        for match in matches:
            section_text = match.group(0)
            for em in re.finditer(EMAIL_CLEAN, section_text):
                email = em.group(1).strip()
                if '.ch' in email:
                    email = email.split('.ch')[0] + '.ch'
                elif '.com' in email:
                    email = email.split('.com')[0] + '.com'
                
                if email in seen_emails or len(email) > 50 or 'www' in email.lower():
                    continue
                seen_emails.add(email)
                
                em_start = max(0, match.start() + em.start() - 150)
                em_end = min(len(txt), match.start() + em.end() + 150)
                context = txt[em_start:em_end]
                
                name = None
                lines = context.splitlines()
                for i, ln in enumerate(lines):
                    if email in ln:
                        before_email = ln[:ln.index(email)].strip()
                        words = before_email.split()
                        has_number = re.search(r'\d+$', before_email)
                        has_street = re.search(r'Allee|Strasse|Weg|Platz', before_email, re.I)
                        has_plz = re.search(r'\d{4}', before_email)
                        if 2 <= len(words) <= 4 and not has_number and not has_street and not has_plz:
                            name = before_email
                        
                        if not name and i > 0:
                            prev = lines[i-1].strip()
                            words = prev.split()
                            has_number = re.search(r'\d+$', prev)
                            has_street = re.search(r'Allee|Strasse|Weg|Platz', prev, re.I)
                            has_plz = re.search(r'\d{4}', prev)
                            if 2 <= len(words) <= 4 and not has_number and not has_street and not has_plz:
                                name = prev
                        
                        if not name:
                            for j in range(max(0, i-3), min(len(lines), i+2)):
                                check = lines[j].strip()
                                has_company = re.search(r'\b(AG|GmbH|consero)\b', check, re.I)
                                if has_company and len(check.split()) <= 4:
                                    has_street_c = re.search(r'Allee|Strasse|Weg|Platz', check, re.I)
                                    has_plz_c = re.search(r'\d{4}', check)
                                    if not has_street_c and not has_plz_c:
                                        name = check
                                        break
                        break
                
                telefon = None
                for ln in lines:
                    if email in ln:
                        phone_match = re.search(PHONE_PATTERN, ln)
                        if phone_match:
                            telefon = phone_match.group(1).strip()
                            break
                
                if not telefon:
                    phone_context = txt[match.start() + em.start():match.start() + em.end() + 300]
                    phone_match = re.search(PHONE_PATTERN, phone_context)
                    if phone_match:
                        telefon = phone_match.group(1).strip()
                
                if telefon:
                    telefon = re.sub(r'\s+', ' ', telefon)
                
                contacts.append({"name": name, "telefon": telefon, "email": email})
    
    unique = []
    seen = set()
    for c in contacts:
        if c["email"] not in seen:
            seen.add(c["email"])
            unique.append(c)
    return unique

def extract_kriterien(txt):
    sec = get_section_block(txt, r"^4\b")
    if not sec or len(sec) < 50:
        return []
    kriterien = []
    for ln in sec.splitlines():
        s = ln.strip()
        if re.match(r"^\d+\.?\d*\s+", s):
            continue
        if re.search(r"(?i)(Reihenfolge|Gewichtung|Massgebend)", s):
            break
        if re.match(r"^[•\-]\s+", s):
            item = re.sub(r"^[•\-]\s+", "", s).strip()
            if len(item) > 15 and not re.search(r"(Zürich|Luzern|Emmen|Weggis|Brun)", item, re.I):
                kriterien.append(item)
    return kriterien

def extract_teilnehmende(txt):
    m = re.search(r"(?is)Teilnehmende.*?zugelassen:\s*(?P<blk>(?:\n|.)*?)(?:\n\s*\d+\.\d+|\Z)", txt)
    if not m: 
        return []
    blk = m.group('blk')
    names = [re.sub(r"^[•\-\s]+","",ln).strip() for ln in blk.splitlines() if ln.strip()]
    return [n for n in names if any(c.isalpha() for c in n)]

def extract_raumprogramm(txt: str):
    """
    Extrahiert das Raumprogramm aus dem Text.
    
    Unterstützt verschiedene Formate:
    - Numerische Raumnummern: 1.01, 2.03
    - Alphanumerische Raumnummern: EG-01, 1OG-02, UG-01
    
    Returns:
        Liste von Dictionaries mit Rauminformationen
    """
    raeume = []
    
    # Suche nach Tabellen-Header direkt (robuster als nach Kapitelnummer zu suchen)
    # Pattern: "Raumnummer Raumname Fläche [m²] Anzahl Geschoss" oder ohne [m²]
    header_pattern = r"Raumnummer\s+Raumname\s+Fläche\s+(?:\[m²\])?\s*Anzahl\s+Geschoss"
    
    # Finde alle Header-Vorkommen (es könnte mehrere Tabellen geben)
    for header_match in re.finditer(header_pattern, txt, re.IGNORECASE):
        # Extrahiere Text ab diesem Header bis zum nächsten großen Kapitel
        start_pos = header_match.end()
        
        # Finde Ende: Nächstes großes Kapitel (z.B. "4 Beurteilungskriterien") 
        # oder nächster Tabellen-Header
        end_match = re.search(r"\n\s*(?:[4-9]\s+[A-Z][a-z]+|Raumnummer\s+Raumname)", txt[start_pos:], re.IGNORECASE)
        if end_match:
            end_pos = start_pos + end_match.start()
        else:
            end_pos = len(txt)
        
        table_text = txt[start_pos:end_pos]
        lines = table_text.splitlines()
        
        # Parse die Zeilen
        for line in lines:
            stripped = line.strip()
            if not stripped or len(stripped) < 10:
                continue
            
            # Skip Überschriften wie "Erdgeschoss (EG)", "Brun Emmenweid", etc.
            if re.search(r"(?i)(Erdgeschoss|Obergeschoss|Untergeschoss|Dachgeschoss|Brun\s+Emmen|typisches|optional|falls vorgesehen)", stripped):
                continue
            
            # Pattern für Datenzeilen
            # Format: "EG-01 Eingangsbereich / Lobby 120 1 EG"
            pattern = r"^(?P<nr>[A-Z0-9\.-]+)\s+(?P<n>.+?)\s+(?P<flaeche>\d+(?:[.,]\d+)?)\s+(?P<anzahl>\d+)\s+(?P<geschoss>[A-Z0-9\.\s]+)$"
            
            match = re.match(pattern, stripped)
            if match:
                try:
                    raum_nr = match.group('nr').strip()
                    raum_name = match.group('n').strip()
                    
                    # Fläche konvertieren
                    flaeche_str = match.group('flaeche').replace(',', '.')
                    flaeche = float(flaeche_str)
                    
                    # Anzahl
                    anzahl = int(match.group('anzahl'))
                    
                    # Geschoss
                    geschoss = match.group('geschoss').strip()
                    
                    # Validierung: Name sollte Buchstaben und mindestens 3 Zeichen haben
                    # Und nicht bereits vorhanden sein (Duplikate vermeiden)
                    if len(raum_name) >= 3 and any(c.isalpha() for c in raum_name):
                        # Prüfe ob bereits vorhanden
                        if not any(r['raumnummer'] == raum_nr for r in raeume):
                            raeume.append({
                                'raumnummer': raum_nr,
                                'raumname': raum_name,
                                'flaeche': flaeche,
                                'anzahl': anzahl,
                                'geschoss': geschoss
                            })
                except Exception as e:
                    # Fehler beim Parsen ignorieren
                    pass
    
    return raeume

def parse_text(txt: str, validate: bool = False, validator=None) -> dict:
    """
    Parst den Text und extrahiert alle Wettbewerbsinformationen.
    
    Args:
        txt: Der zu parsende Text
        validate: Ob LLM-Validierung durchgeführt werden soll
        validator: Optional ein LLMValidator-Objekt
    
    Returns:
        Dictionary mit extrahierten Daten (und optional Validierungsergebnissen)
    """
    extracted_data = {
        "abgabetermin": extract_abgabetermin(txt),
        "besichtigung": extract_besichtigung(txt),
        "kontakte": extract_contacts(txt),
        "abgabeort": extract_abgabeort(txt),
        "einzureichende_unterlagen": extract_unterlagen(txt),
        "beurteilungskriterien": extract_kriterien(txt),
        "teilnehmende": extract_teilnehmende(txt),
        "raumprogramm": extract_raumprogramm(txt),
        "sektionen": extract_sections(txt),
        "meta": {"length": len(txt)}
    }
    
    # Optional: LLM-Validierung
    if validate and validator:
        try:
            validation_results = validator.validate_all(extracted_data, txt)
            extracted_data["llm_validation"] = validation_results
        except Exception as e:
            extracted_data["llm_validation"] = {
                "error": f"Validierung fehlgeschlagen: {str(e)}",
                "status": "failed"
            }
    
    return extracted_data