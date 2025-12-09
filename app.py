import streamlit as st
import pandas as pd
from extractor.core import parse_text
import json

st.set_page_config(page_title="Wettbewerb Extractor", layout="wide")
st.title("🏗️ Wettbewerb Extractor")

data = None
txt = ""

uploaded = st.file_uploader("📄 PDF oder TXT hochladen", type=["pdf","txt"])

if uploaded:
    with st.spinner("Extrahiere Daten..."):
        if uploaded.name.lower().endswith(".pdf"):
            import pdfplumber
            txt_pages = []
            with pdfplumber.open(uploaded) as pdf:
                for p in pdf.pages:
                    t = p.extract_text(x_tolerance=1, y_tolerance=1) or ""
                    if not t.strip():
                        t = p.extract_text() or ""
                    txt_pages.append(t)
            txt = "\n".join(txt_pages)
        else:
            txt = uploaded.read().decode("utf-8", errors="ignore")

        data = parse_text(txt)
        st.success("✅ Extraktion abgeschlossen!")

# --- Ab hier NUR rendern, wenn data vorhanden ist ---
if data:
    # Hauptmetriken
    st.header("📊 Wichtigste Termine")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        abg = data.get("abgabetermin", {})
        if abg and abg.get("iso"):
            date_str = f"{abg.get('iso', '—')} {abg.get('time', '')}".strip()
            st.metric("🗓️ Abgabetermin", date_str)
            # Debug-Info in Expander
            if abg.get("source"):
                with st.expander("ℹ️ Quelle"):
                    st.code(f"Gefunden in: {abg['source']}\nRohtext: {abg.get('raw', '')}", language="text")
        else:
            st.metric("🗓️ Abgabetermin", "—")
            st.warning("⚠️ Kein Abgabetermin gefunden")
    
    with c2:
        bes = data.get("besichtigung", {})
        if bes and bes.get("iso"):
            date_str = f"{bes.get('iso', '—')} {bes.get('time', '')}".strip()
            st.metric("👁️ Besichtigung", date_str)
            if bes.get("treffpunkt"):
                st.caption(f"📍 {bes['treffpunkt']}")
        else:
            st.metric("👁️ Besichtigung", "—")
    
    with c3:
        teilnehmende = data.get("teilnehmende", [])
        st.metric("👥 Teilnehmende", len(teilnehmende))

    # Abgabeort / Adresse
    st.header("📍 Abgabeort / Adresse")
    abg_ort = data.get("abgabeort") or {}
    if abg_ort and abg_ort.get("raw_block"):
        st.info(abg_ort.get("raw_block", ""))
    else:
        st.write("—")

    # Zwei Spalten Layout für Unterlagen und Kriterien
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("📋 Einzureichende Unterlagen")
        unterlagen = data.get("einzureichende_unterlagen", [])
        if unterlagen:
            for i, u in enumerate(unterlagen, 1):
                st.write(f"{i}. {u}")
        else:
            st.write("—")

    with col2:
        st.header("⭐ Beurteilungskriterien")
        kriterien = data.get("beurteilungskriterien", [])
        if kriterien:
            for i, k in enumerate(kriterien, 1):
                st.write(f"{i}. {k}")
        else:
            st.write("—")

    # Teilnehmende
    if teilnehmende:
        st.header("👥 Teilnehmende Teams")
        cols = st.columns(min(len(teilnehmende), 3))
        for i, name in enumerate(teilnehmende):
            with cols[i % 3]:
                st.success(f"✓ {name}")

    # Kontakte als Tabelle
    st.header("📞 Kontakte")
    kontakte = data.get("kontakte", [])
    if kontakte:
        df = pd.DataFrame(kontakte)
        # Formatierung: nur relevante Spalten anzeigen
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.write("—")

    # Export-Funktionen
    st.header("💾 Export")
    col_export1, col_export2 = st.columns(2)
    
    with col_export1:
        # JSON Export
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 Als JSON herunterladen",
            data=json_str,
            file_name=f"{uploaded.name.replace('.pdf', '')}_extrahiert.json",
            mime="application/json"
        )
    
    with col_export2:
        # Excel Export (optional - nur wenn Kontakte vorhanden)
        if kontakte:
            try:
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    pd.DataFrame(kontakte).to_excel(writer, sheet_name='Kontakte', index=False)
                    if teilnehmende:
                        pd.DataFrame({'Teilnehmer': teilnehmende}).to_excel(writer, sheet_name='Teilnehmende', index=False)
                output.seek(0)
                st.download_button(
                    label="📥 Als Excel herunterladen",
                    data=output,
                    file_name=f"{uploaded.name.replace('.pdf', '')}_kontakte.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except ImportError:
                st.caption("⚠️ Excel-Export benötigt 'openpyxl' Package")

    # Debug-Bereich
    with st.expander("🔍 Debug: Alle extrahierten Daten (JSON)"):
        st.json(data)
    
    with st.expander("📄 Debug: Rohtext (erste 5000 Zeichen)"):
        st.text_area("Text", value=txt[:5000], height=300, disabled=True)
    
    # Statistiken
    with st.expander("📊 Statistiken"):
        st.write(f"**Textlänge:** {data['meta']['length']:,} Zeichen")
        st.write(f"**Anzahl Sektionen:** {len(data.get('sektionen', []))}")
        st.write(f"**Anzahl Kontakte:** {len(kontakte)}")
        st.write(f"**Anzahl Unterlagen:** {len(unterlagen)}")
        st.write(f"**Anzahl Kriterien:** {len(kriterien)}")

else:
    st.info("👆 Bitte lade eine PDF/TXT hoch, um die Extraktion zu starten.")
    
    # Hilfetext
    st.markdown("""
    ### 📖 So funktioniert's:
    1. Lade ein PDF oder TXT-Dokument eines Architekturwettbewerbs hoch
    2. Das System extrahiert automatisch wichtige Informationen:
       - Abgabetermin und Besichtigungstermin
       - Einzureichende Unterlagen
       - Beurteilungskriterien
       - Kontaktdaten
       - Teilnehmende Teams
    3. Exportiere die Daten als JSON oder Excel
    
    ### 🎯 Unterstützte Formate:
    - PDF-Dokumente
    - TXT-Dateien
    """)