# test_contacts.py - Test fuer Kontakte-Extraktion
import re
import pdfplumber

pdf_path = "Emmenbrücke.pdf"

print("Lese PDF...")
with pdfplumber.open(pdf_path) as pdf:
    txt = "\n".join((p.extract_text() or "") for p in pdf.pages)

print(f"PDF gelesen: {len(txt)} Zeichen\n")

print("="*80)
print("TEST: NEUE Kontakt-Extraktion")
print("="*80)

def extract_contacts_new(txt):
    contacts = []
    seen_emails = set()
    
    EMAIL_CLEAN = r"(?<![a-zA-Z0-9])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![a-zA-Z0-9])"
    PHONE_PATTERN = r"(?:t\s+)?(\+?\d{1,3}[\s\-]?\d{1,3}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2})"
    
    section_patterns = [
        r"(?i)Bauherrenvertretung.*?(?=\n\d+\.\d+|\Z)",
        r"(?i)Leitung\s+und\s+Sekretariat.*?(?=\n\d+\.|\Z)",
        r"(?i)2\.13.*?Leitung.*?Sekretariat.*?(?=\n3\.|\Z)",
        r"(?i)2\.2.*?Bauherrenvertretung.*?(?=\n2\.3|\Z)",
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
                elif '.de' in email:
                    email = email.split('.de')[0] + '.de'
                
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
                        has_number_at_end = re.search(r'\d+
                
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
                
                if not telefon:
                    phone_context_before = txt[max(0, match.start() + em.start() - 200):match.start() + em.start()]
                    phone_match = re.search(PHONE_PATTERN, phone_context_before)
                    if phone_match:
                        telefon = phone_match.group(1).strip()
                
                if telefon:
                    telefon = re.sub(r'\s+', ' ', telefon)
                
                contacts.append({
                    "name": name,
                    "telefon": telefon,
                    "email": email
                })
    
    unique_contacts = []
    seen = set()
    for c in contacts:
        if c["email"] not in seen:
            seen.add(c["email"])
            unique_contacts.append(c)
    
    return unique_contacts

new_contacts = extract_contacts_new(txt)

print(f"\nGefundene Kontakte: {len(new_contacts)}\n")

for i, c in enumerate(new_contacts, 1):
    print(f"{i}. Name: {c['name'] or '---'}")
    print(f"   Telefon: {c['telefon'] or '---'}")
    print(f"   E-Mail: {c['email']}")
    
    issues = []
    if c['email'] and ('www' in c['email'] or len(c['email']) > 50):
        issues.append("FEHLER E-Mail")
    else:
        issues.append("OK E-Mail")
    
    if c['telefon']:
        digits = re.sub(r'[^\d]', '', c['telefon'])
        if len(digits) < 8 or len(digits) > 15:
            issues.append("FEHLER Telefon")
        else:
            issues.append("OK Telefon")
    else:
        issues.append("KEIN Telefon")
    
    if c['name'] and re.search(r'\d{4}', c['name']):
        issues.append("FEHLER Name")
    elif c['name']:
        issues.append("OK Name")
    else:
        issues.append("KEIN Name")
    
    print(f"   Status: {' | '.join(issues)}")
    print()

print("="*80)
print("FERTIG")
print("="*80)
, before_email)
                        has_street = re.search(r'Allee|Strasse|Weg|Platz', before_email, re.I)
                        has_plz = re.search(r'\d{4}', before_email)
                        
                        if 2 <= len(words) <= 4 and not has_number_at_end and not has_street and not has_plz:
                            name = before_email
                        
                        if not name and i > 0:
                            prev = lines[i-1].strip()
                            words = prev.split()
                            has_number_at_end = re.search(r'\d+
                
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
                
                if not telefon:
                    phone_context_before = txt[max(0, match.start() + em.start() - 200):match.start() + em.start()]
                    phone_match = re.search(PHONE_PATTERN, phone_context_before)
                    if phone_match:
                        telefon = phone_match.group(1).strip()
                
                if telefon:
                    telefon = re.sub(r'\s+', ' ', telefon)
                
                contacts.append({
                    "name": name,
                    "telefon": telefon,
                    "email": email
                })
    
    unique_contacts = []
    seen = set()
    for c in contacts:
        if c["email"] not in seen:
            seen.add(c["email"])
            unique_contacts.append(c)
    
    return unique_contacts

new_contacts = extract_contacts_new(txt)

print(f"\nGefundene Kontakte: {len(new_contacts)}\n")

for i, c in enumerate(new_contacts, 1):
    print(f"{i}. Name: {c['name'] or '---'}")
    print(f"   Telefon: {c['telefon'] or '---'}")
    print(f"   E-Mail: {c['email']}")
    
    issues = []
    if c['email'] and ('www' in c['email'] or len(c['email']) > 50):
        issues.append("FEHLER E-Mail")
    else:
        issues.append("OK E-Mail")
    
    if c['telefon']:
        digits = re.sub(r'[^\d]', '', c['telefon'])
        if len(digits) < 8 or len(digits) > 15:
            issues.append("FEHLER Telefon")
        else:
            issues.append("OK Telefon")
    else:
        issues.append("KEIN Telefon")
    
    if c['name'] and re.search(r'\d{4}', c['name']):
        issues.append("FEHLER Name")
    elif c['name']:
        issues.append("OK Name")
    else:
        issues.append("KEIN Name")
    
    print(f"   Status: {' | '.join(issues)}")
    print()

print("="*80)
print("FERTIG")
print("="*80)
, prev)
                            has_street = re.search(r'Allee|Strasse|Weg|Platz', prev, re.I)
                            has_plz = re.search(r'\d{4}', prev)
                            
                            if 2 <= len(words) <= 4 and not has_number_at_end and not has_street and not has_plz:
                                name = prev
                        
                        if not name and i > 1:
                            prev2 = lines[i-2].strip()
                            words = prev2.split()
                            has_number_at_end = re.search(r'\d+'
                
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
                
                if not telefon:
                    phone_context_before = txt[max(0, match.start() + em.start() - 200):match.start() + em.start()]
                    phone_match = re.search(PHONE_PATTERN, phone_context_before)
                    if phone_match:
                        telefon = phone_match.group(1).strip()
                
                if telefon:
                    telefon = re.sub(r'\s+', ' ', telefon)
                
                contacts.append({
                    "name": name,
                    "telefon": telefon,
                    "email": email
                })
    
    unique_contacts = []
    seen = set()
    for c in contacts:
        if c["email"] not in seen:
            seen.add(c["email"])
            unique_contacts.append(c)
    
    return unique_contacts

new_contacts = extract_contacts_new(txt)

print(f"\nGefundene Kontakte: {len(new_contacts)}\n")

for i, c in enumerate(new_contacts, 1):
    print(f"{i}. Name: {c['name'] or '---'}")
    print(f"   Telefon: {c['telefon'] or '---'}")
    print(f"   E-Mail: {c['email']}")
    
    issues = []
    if c['email'] and ('www' in c['email'] or len(c['email']) > 50):
        issues.append("FEHLER E-Mail")
    else:
        issues.append("OK E-Mail")
    
    if c['telefon']:
        digits = re.sub(r'[^\d]', '', c['telefon'])
        if len(digits) < 8 or len(digits) > 15:
            issues.append("FEHLER Telefon")
        else:
            issues.append("OK Telefon")
    else:
        issues.append("KEIN Telefon")
    
    if c['name'] and re.search(r'\d{4}', c['name']):
        issues.append("FEHLER Name")
    elif c['name']:
        issues.append("OK Name")
    else:
        issues.append("KEIN Name")
    
    print(f"   Status: {' | '.join(issues)}")
    print()

print("="*80)
print("FERTIG")
print("="*80)
, prev2)
                            has_street = re.search(r'Allee|Strasse|Weg|Platz', prev2, re.I)
                            has_plz = re.search(r'\d{4}', prev2)
                            
                            if 2 <= len(words) <= 4 and not has_number_at_end and not has_street and not has_plz:
                                name = prev2
                        
                        # Spezialfall: Suche nach Firmennamen mit AG, GmbH etc. in den naechsten Zeilen
                        if not name:
                            for j in range(max(0, i-3), min(len(lines), i+2)):
                                check_line = lines[j].strip()
                                if re.search(r'\b(AG|GmbH|consero)\b', check_line, re.I) and len(check_line.split()) <= 4:
                                    has_street_check = re.search(r'Allee|Strasse|Weg|Platz', check_line, re.I)
                                    has_plz_check = re.search(r'\d{4}', check_line)
                                    if not has_street_check and not has_plz_check:
                                        name = check_line
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
                
                if not telefon:
                    phone_context_before = txt[max(0, match.start() + em.start() - 200):match.start() + em.start()]
                    phone_match = re.search(PHONE_PATTERN, phone_context_before)
                    if phone_match:
                        telefon = phone_match.group(1).strip()
                
                if telefon:
                    telefon = re.sub(r'\s+', ' ', telefon)
                
                contacts.append({
                    "name": name,
                    "telefon": telefon,
                    "email": email
                })
    
    unique_contacts = []
    seen = set()
    for c in contacts:
        if c["email"] not in seen:
            seen.add(c["email"])
            unique_contacts.append(c)
    
    return unique_contacts

new_contacts = extract_contacts_new(txt)

print(f"\nGefundene Kontakte: {len(new_contacts)}\n")

for i, c in enumerate(new_contacts, 1):
    print(f"{i}. Name: {c['name'] or '---'}")
    print(f"   Telefon: {c['telefon'] or '---'}")
    print(f"   E-Mail: {c['email']}")
    
    issues = []
    if c['email'] and ('www' in c['email'] or len(c['email']) > 50):
        issues.append("FEHLER E-Mail")
    else:
        issues.append("OK E-Mail")
    
    if c['telefon']:
        digits = re.sub(r'[^\d]', '', c['telefon'])
        if len(digits) < 8 or len(digits) > 15:
            issues.append("FEHLER Telefon")
        else:
            issues.append("OK Telefon")
    else:
        issues.append("KEIN Telefon")
    
    if c['name'] and re.search(r'\d{4}', c['name']):
        issues.append("FEHLER Name")
    elif c['name']:
        issues.append("OK Name")
    else:
        issues.append("KEIN Name")
    
    print(f"   Status: {' | '.join(issues)}")
    print()

print("="*80)
print("FERTIG")
print("="*80)