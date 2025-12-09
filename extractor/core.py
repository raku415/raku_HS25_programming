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
    Liefert den Textblock einer Sektion, deren Titel auf title_regex matched.
    Nutzt das bestehende Überschriftenmuster SEC_HEAD.
    """
    secs = list(re.finditer(SEC_HEAD, txt))
    for i, m in enumerate(secs):
        title = m.group('title')
        if re.search(title_regex, title, flags=re.I):
            start = m.start()
            end = secs[i+1].start() if i+1 < len(secs) else len(txt)
            return txt[start:end]
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
    Preferenziert Datum/Zeit im Abschnitt, dessen Titel 'Abgabe'/'Eingabe' enthält.
    Fällt andernfalls auf Kapitel 3.* (Termine) zurück, ignoriert aber 'Programm/Genehmigung'.
    """
    txt_no_toc = strip_toc(txt)

    # 1) Nur im "Abgabe/Eingabe"-Abschnitt suchen (z. B. "3.7 Abgabetermin und Eingabeort")
    sec = get_section_block(txt_no_toc, r"\b(Abgabe(?:termin)?|Eingabe(?:termin)?|Eingabeort|Abgabeort)\b")
    candidates = []
    if sec:
        # Trefferzeilen, die Abgabe/Eingabe enthalten
        for ln in sec.splitlines():
            if re.search(r"(?i)\b(Abgabe|Eingabe|Planunterlagen|Verfassercouvert)\b", ln):
                m = re.search(DATE_TIME, ln)
                if m:
                    candidates.append(("section", ln.strip(), m.group('date'), m.group('time')))

        # Falls Datum nicht in derselben Zeile steht: nachfolgende 3–4 Zeilen scannen
        lines = sec.splitlines()
        for i, ln in enumerate(lines):
            if re.search(r"(?i)\b(Abgabe|Eingabe|Planunterlagen|Verfassercouvert)\b", ln) and i+1 < len(lines):
                win = "\n".join(lines[i+1:i+5])
                m = re.search(DATE_TIME, win)
                if m:
                    raw = (ln + " " + m.group(0)).strip()
                    candidates.append(("section_follow", raw, m.group('date'), m.group('time')))

    # 2) Fallback: Innerhalb Kapitel 3.* (Termine) nach typischen Abgabezeilen suchen
    if not candidates:
        m3 = re.search(r"(?is)\n3\.\s.*?(?P<blk>(?:\n.+?)+?)(?:\n\d+\.\s|$)", txt_no_toc)
        if m3:
            blk = m3.group('blk')
            for ln in blk.splitlines():
                if re.search(r"(?i)\b(Abgabe|Eingabe|Planunterlagen|Verfassercouvert)\b", ln):
                    m = re.search(DATE_TIME, ln)
                    if m:
                        candidates.append(("kap3", ln.strip(), m.group('date'), m.group('time')))

    # 3) Als allerletztes (nur wenn gar nichts gefunden): globales starkes Muster
    if not candidates:
        strong = re.search(
            r"(?is)(?:Abgabe(?:termin)?|Eingabe(?:termin)?|Planunterlagen|Verfassercouvert).*?"
            r"(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4})(?:[, ]+\s*(?P<time>\d{1,2}:\d{2})\s*h?)?",
            txt_no_toc
        )
        if strong:
            candidates.append(("global", strong.group(0).splitlines()[0].strip(),
                               strong.group('date'), strong.group('time')))

    # 4) Kandidaten filtern: keine Programm-/Genehmigung-/Beschluss-Zeilen zulassen
    filtered = []
    for src, raw, d, t in candidates:
        if re.search(r"(?i)\b(Programm|Genehmigung|Beschluss|Protokoll)\b", raw):
            continue
        filtered.append((src, raw, d, t))

    if not filtered:
        return {}

    # 5) Besten Kandidaten wählen: Bevorzugt aus 'section'/'section_follow', dann 'kap3', dann 'global'
    priority = {"section": 3, "section_follow": 2, "kap3": 1, "global": 0}
    best = max(filtered, key=lambda x: priority.get(x[0], 0))
    iso, time = norm_date(best[2], best[3])
    return {"raw": best[1], "iso": iso, "time": time}


def extract_unterlagen(txt: str):
    """
    Sucht 'Einzureichende Unterlagen' (oder Varianten) und sammelt Bullet-Punkte.
    Endet vor der nächsten nummerierten Überschrift (z. B. '5.1' oder '6').
    """
    patterns = [
        r"(?is)\bEinzureichende\s+Unterlagen\b",
        r"(?is)\bEinreichung(?:\s*der)?\s*Unterlagen\b",
        r"(?is)\bAbgabeinhalt\b",
    ]
    for pat in patterns:
        m = re.search(pat + r".*?(?P<blk>(?:\n.+?)+?)(?:\n\s*\d+(?:\.\d+)*\s+[A-ZÄÖÜa-zäöü]|$)", txt)
        if not m:
            continue
        bullets = _collect_bullets(m.group('blk'))
        if bullets:
            return bullets
        # Fallback, falls keine klassischen Bullets verwendet wurden:
        rough = [ln.strip() for ln in m.group('blk').splitlines()
                 if len(ln.strip()) > 3 and not re.match(r"^\s*\d+(?:\.\d+)*\s", ln)]
        if rough:
            return rough
    return []

def extract_abgabeort(txt: str):
    """
    Sucht 'Abgabeort'/'Eingabeort'/'Abgabeadresse'/'Eingabeadresse' und liefert
    einen kleinen Rohblock mit den wahrscheinlich relevanten Zeilen (Adresse).
    """
    anchors = [
        r"(?i)\bAbgabeort\b",
        r"(?i)\bEingabeort\b",
        r"(?i)\bAbgabeadresse\b",
        r"(?i)\bEingabeadresse\b",
        r"(?i)\bEingabe\b",  # generisch, nur als letzter Versuch
    ]
    for a in anchors:
        m = re.search(a, txt)
        if not m:
            continue
        start = max(0, m.start() - 200)
        end   = min(len(txt), m.end() + 400)
        window = txt[start:end]

        candidates = []
        for ln in window.splitlines():
            s = ln.strip()
            if not s:
                continue
            if re.search(r"\b\d{4}\s+[A-ZÄÖÜa-zäöü\- ]+\b", s):  # 4-stellige CH-PLZ
                candidates.append(s)
            elif re.search(r"(?i)(strasse|straße|allee|platz|weg)\b", s):
                candidates.append(s)
            elif re.search(r"(?i)(Sekretariat|c/o|z\.Hd\.)", s):
                candidates.append(s)

        lines = window.splitlines()
        idx_anchor = 0
        cum = 0
        for i, ln in enumerate(lines):
            cum += len(ln) + 1
            if cum >= (m.start() - start):
                idx_anchor = i
                break

        near = [lines[i].strip() for i in range(idx_anchor, min(idx_anchor+6, len(lines))) if lines[i].strip()]

        merged = []
        for s in near + candidates:
            if s and s not in merged:
                merged.append(s)

        if merged:
            return {"raw_block": "\n".join(merged[:6]), "lines": merged[:6]}

    return {}

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
        "abgabeort": extract_abgabeort(txt),
        "einzureichende_unterlagen": extract_unterlagen(txt),
        "beurteilungskriterien": extract_kriterien(txt),
        "teilnehmende": extract_teilnehmende(txt),
        "sektionen": extract_sections(txt),
        "meta": {"length": len(txt)}
    }
    return data
