# app.py
import streamlit as st
import pandas as pd
from extractor.core import parse_text

st.set_page_config(page_title="Wettbewerb Extractor", layout="wide")
st.title("Wettbewerb Extractor")

uploaded = st.file_uploader("PDF oder TXT hochladen", type=["pdf","txt"])
if uploaded:
    if uploaded.name.lower().endswith(".pdf"):
        import pdfplumber
        with pdfplumber.open(uploaded) as pdf:
            txt = "\n".join((p.extract_text() or "") for p in pdf.pages)
    else:
        txt = uploaded.read().decode("utf-8", errors="ignore")

    data = parse_text(txt)

    st.subheader("Ergebnis (JSON)")
    st.json(data)

    # Beispiel: falls du Listen/Felder als Tabelle zeigen willst
    if isinstance(data, dict) and "kontakte" in data:
        st.subheader("Kontakte")
        st.dataframe(pd.DataFrame(data["kontakte"]))
