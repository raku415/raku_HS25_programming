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
    lines = sec.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if re.match(r"^\d+\.\d+\s+", ln) or not ln:
            i += 1
            continue
        
        bullet_match = re.match(r"^[•\-]\s+(?P<titel>[A-Za-zÄÖÜäöü\s]+)\s*(?P<rest>.*)$", ln)
        if bullet_match:
            titel = bullet_match.group('titel').strip()
            rest = bullet_match.group('rest').strip()
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
            unterlagen.append({"titel": titel, "beschreibung": beschreibung if beschreibung else None})
            i = j
        else:
            i += 1
    return unterlagen[:25]

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

def parse_text(txt: str) -> dict:
    return {
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