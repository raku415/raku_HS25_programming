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

def norm_date(d, t=None):
    if not d: 
        return None, None
    dt = dateparser.parse(f"{d} {t or ''}", languages=['de'])
    if not dt: 
        return None, None
    return dt.date().isoformat(), dt.strftime("%H:%M") if t else None

# --- Einzel-Extractor ---
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
    m = re.search(ABGABE, txt)
    if not m: 
        return {}
    line = m.group('line')
    m2 = re.search(DATE_TIME, line)
    if not m2: 
        return {"raw": line.strip()}
    iso, time = norm_date(m2.group('date'), m2.group('time'))
    return {"raw": line.strip(), "iso": iso, "time": time}

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
    # Sucht Überschrift „Beurteilungskriterien“ (z. B. 4 Beurteilungskriterien) und sammelt Bullet-Zeilen
    block = re.search(r"(?is)\bBeurteilungskriterien\b.*?(?P<li>(?:\n\s*(?:•|\-).+)+)", txt)
    if not block: 
        return []
    return [re.sub(r"^\s*(?:•|\-)\s*", "", ln).strip()
            for ln in block.group('li').splitlines() if re.match(r"\s*(?:•|\-)\s*", ln)]

def extract_teilnehmende(txt):
    # sucht „Teilnehmende … zugelassen:“ bis zur nächsten nummerierten Überschrift
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
        "beurteilungskriterien": extract_kriterien(txt),
        "teilnehmende": extract_teilnehmende(txt),
        "sektionen": extract_sections(txt),
        "meta": {"length": len(txt)}
    }
    return data
