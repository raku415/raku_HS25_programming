# app.py (nur der relevante Teil)
import streamlit as st
import pandas as pd
from extractor.core import parse_text

st.set_page_config(page_title="Wettbewerb Extractor", layout="wide")
st.title("Wettbewerb Extractor")

uploaded = st.file_uploader("PDF oder TXT hochladen", type=["pdf","txt"])
if uploaded:
    if uploaded.name.lower().endswith(".pdf"):
        import pdfplumber
        txt_pages = []
        with pdfplumber.open(uploaded) as pdf:
            for p in pdf.pages:
                t = p.extract_text(x_tolerance=1, y_tolerance=1) or ""
                # Fallback: wenn leer, versuch .extract_text() ohne Parameter
                if not t.strip():
                    t = p.extract_text() or ""
                txt_pages.append(t)
        txt = "\n".join(txt_pages)
    else:
        txt = uploaded.read().decode("utf-8", errors="ignore")

    data = parse_text(txt)

st.subheader("Abgabeort / Adresse")
abg_ort = data.get("abgabeort") or {}
if abg_ort:
    st.code(abg_ort.get("raw_block", ""), language="text")
else:
    st.write("—")

st.subheader("Einzureichende Unterlagen")
unterlagen = data.get("einzureichende_unterlagen", [])
if unterlagen:
    for u in unterlagen:
        st.write(f"• {u}")
else:
    st.write("—")


    # KPIs
    c1,c2,c3 = st.columns(3)
    with c1:
        abg = data.get("abgabetermin", {})
        st.metric("Abgabetermin", f"{(abg.get('iso') or '—')} {(abg.get('time') or '')}".strip())
    with c2:
        bes = data.get("besichtigung", {})
        st.metric("Besichtigung", f"{(bes.get('iso') or '—')} {(bes.get('time') or '')}".strip())
    with c3:
        st.metric("Teilnehmende (Anzahl)", len(data.get("teilnehmende", [])))

    st.subheader("Beurteilungskriterien")
    if data.get("beurteilungskriterien"):
        for k in data["beurteilungskriterien"]:
            st.write(f"• {k}")
    else:
        st.write("—")

    st.subheader("Kontakte")
    if data.get("kontakte"):
        st.dataframe(pd.DataFrame(data["kontakte"]))
    else:
        st.write("—")

    st.subheader("Teilnehmende")
    st.write(", ".join(data.get("teilnehmende", [])) or "—")

    with st.expander("Rohtext (Debug)"):
        st.text_area("Text", value=txt[:5000], height=300)
    

