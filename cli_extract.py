# cli_extract.py
import argparse, json, sys, pathlib
from extractor.core import parse_text

def read_pdf(path: str) -> str:
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)

def main():
    ap = argparse.ArgumentParser(description="Wettbewerb-Extractor")
    ap.add_argument("input", help="Pfad zur PDF- oder TXT-Datei")
    ap.add_argument("-o", "--out", help="Output JSON-Datei", default=None)
    args = ap.parse_args()

    p = pathlib.Path(args.input)
    if not p.exists():
        print(f"Datei nicht gefunden: {p}", file=sys.stderr); sys.exit(1)

    if p.suffix.lower() == ".pdf":
        txt = read_pdf(str(p))
    else:
        txt = p.read_text(encoding="utf-8", errors="ignore")

    data = parse_text(txt)
    js = json.dumps(data, ensure_ascii=False, indent=2)

    if args.out:
        pathlib.Path(args.out).write_text(js, encoding="utf-8")
        print(f"✅ geschrieben: {args.out}")
    else:
        print(js)

if __name__ == "__main__":
    main()
