# extractor/core.py
import re, dateparser

SEC_HEAD = r"(?m)^(?P<num>\d+(?:\.\d+)*)\s+(?P<title>[A-ZÄÖÜa-zäöü].+)$"
DATE_TIME = r"(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4})(?:,\s*(?P<time>\d{1,2}:\d{2})\s*h?)?"

def norm_date(d, t=None):
    if not d: return None, None
    dt = dateparser.parse(f"{d} {t or ''}", languages=['de'])
    if not dt: return None, None
    return dt.date().isoformat(), dt.strftime("%H:%M") if t else None

def parse_text(txt: str) -> dict:
    # hier deine Extraktion (Abgabetermin, Besichtigung, Kontakte, Kriterien, …)
    # minimaler Platzhalter:
    return {"length": len(txt)}
