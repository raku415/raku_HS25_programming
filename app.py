import streamlit as st
import pandas as pd
from extractor.core import parse_text
import json

st.set_page_config(
    page_title="Wettbewerb Extractor", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS für besseres Design
st.markdown("""
<style>
    .main-metric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 10px 0;
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
        margin: 5px 0;
    }
    .metric-label {
        font-size: 14px;
        opacity: 0.9;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 10px 0;
    }
    .success-box {
        background-color: #e8f5e9;  /* Hellgrün - für Abgabeort */
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #4caf50;  /* Dunkelgrün */
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3e0;  /* Hellorange */
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #ff9800;  /* Orange */
        margin: 10px 0;
    }
    .primary-box {
        background-color: #e3f2fd;  /* Hellblau */
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #2196f3;  /* Blau */
        margin: 10px 0;
    }
    .stTab {
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

# Seitenleiste
with st.sidebar:
    st.title("🏗️ Wettbewerb Extractor")
    st.markdown("---")
    
    uploaded = st.file_uploader(
        "📄 PDF/TXT hochladen", 
        type=["pdf","txt"],
        help="Lade ein Wettbewerbs-PDF hoch"
    )
    
    if uploaded:
        st.success(f"✅ {uploaded.name}")
        file_size = len(uploaded.getvalue()) / 1024
        st.caption(f"Größe: {file_size:.1f} KB")
    
    st.markdown("---")
    st.markdown("### ℹ️ Über")
    st.caption("Dieses Tool extrahiert automatisch wichtige Informationen aus Architekturwettbewerbs-PDFs.")
    st.caption("Version 1.0")

# Hauptbereich
if not uploaded:
    # Landing Page
    st.title("🏗️ Wettbewerb Extractor Dashboard")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="info-box">
            <h3>📋 Extraktion</h3>
            <p>Automatische Erkennung von Terminen, Unterlagen, Kriterien und Kontakten</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="info-box">
            <h3>📊 Übersicht</h3>
            <p>Dashboard-Ansicht aller wichtigen Wettbewerbs-Informationen</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="info-box">
            <h3>💾 Export</h3>
            <p>Download als JSON oder Excel für weitere Verarbeitung</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.info("👆 Bitte lade ein PDF in der Seitenleiste hoch, um zu starten.")
    
    with st.expander("📖 Anleitung"):
        st.markdown("""
        **So funktioniert's:**
        1. Lade ein Architekturwettbewerbs-PDF über die Seitenleiste hoch
        2. Das System extrahiert automatisch alle relevanten Informationen
        3. Nutze die Tabs zur Navigation durch die verschiedenen Bereiche
        4. Exportiere die Daten als JSON oder Excel
        
        **Unterstützte Datenfelder:**
        - 🗓️ Abgabe- und Besichtigungstermine
        - 📍 Abgabeort und Kontaktdaten
        - 📋 Einzureichende Unterlagen
        - ⭐ Beurteilungskriterien
        - 👥 Teilnehmende Teams
        """)

else:
    # PDF verarbeiten
    data = None
    txt = ""
    
    with st.spinner("🔄 Extrahiere Daten..."):
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
    
    # Tabs für verschiedene Bereiche
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Übersicht", 
        "📋 Unterlagen & Kriterien", 
        "👥 Teilnehmer & Kontakte",
        "💾 Export",
        "🔍 Debug"
    ])
    
    # TAB 1: Übersicht
    with tab1:
        st.header("📊 Wettbewerbs-Übersicht")
        
        # Wichtigste Metriken
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            abg = data.get("abgabetermin", {})
            if abg and abg.get("iso"):
                date_str = f"{abg.get('iso', '—')}"
                time_str = abg.get('time', '—')
                st.markdown(f"""
                <div class="main-metric">
                    <div class="metric-label">🗓️ Abgabetermin</div>
                    <div class="metric-value">{date_str}</div>
                    <div class="metric-label">{time_str}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.metric("🗓️ Abgabetermin", "—")
        
        with col2:
            bes = data.get("besichtigung", {})
            if bes and bes.get("iso"):
                date_str = f"{bes.get('iso', '—')}"
                time_str = bes.get('time', '—')
                st.markdown(f"""
                <div class="main-metric">
                    <div class="metric-label">👁️ Besichtigung</div>
                    <div class="metric-value">{date_str}</div>
                    <div class="metric-label">{time_str}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.metric("👁️ Besichtigung", "—")
        
        with col3:
            teilnehmende = data.get("teilnehmende", [])
            st.markdown(f"""
            <div class="main-metric">
                <div class="metric-label">👥 Teilnehmende</div>
                <div class="metric-value">{len(teilnehmende)}</div>
                <div class="metric-label">Teams</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            kontakte = data.get("kontakte", [])
            st.markdown(f"""
            <div class="main-metric">
                <div class="metric-label">📞 Kontakte</div>
                <div class="metric-value">{len(kontakte)}</div>
                <div class="metric-label">Personen</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Abgabeort
        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            st.subheader("📍 Abgabeort")
            abg_ort = data.get("abgabeort") or {}
            if abg_ort and abg_ort.get("raw_block"):
                st.markdown(f"""
                <div class="success-box">
                    {abg_ort.get("raw_block", "—").replace(chr(10), "<br>")}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Keine Informationen gefunden")
        
        with col_right:
            st.subheader("ℹ️ Statistiken")
            stats = {
                "Textlänge": f"{data['meta']['length']:,} Zeichen",
                "Sektionen": len(data.get('sektionen', [])),
                "Unterlagen": len(data.get('einzureichende_unterlagen', [])),
                "Kriterien": len(data.get('beurteilungskriterien', []))
            }
            for label, value in stats.items():
                st.metric(label, value)
    
    # TAB 2: Unterlagen & Kriterien
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 Einzureichende Unterlagen")
            unterlagen = data.get("einzureichende_unterlagen", [])
            
            if unterlagen:
                # Zeige Einleitung falls vorhanden (ohne Dropdown)
                for item in unterlagen:
                    if isinstance(item, dict) and item.get("typ") == "einleitung":
                        st.info(item.get("beschreibung", ""))
                        break
                
                # Zeige restliche Unterlagen
                counter = 1
                for item in unterlagen:
                    if isinstance(item, dict):
                        # Skip Einleitung (wurde schon angezeigt)
                        if item.get("typ") == "einleitung":
                            continue
                        
                        titel = item.get("titel", "Unterlage")
                        beschreibung = item.get("beschreibung")
                        
                        if beschreibung:
                            # Mit Beschreibung → Expander
                            with st.expander(f"**{counter}. {titel}**", expanded=False):
                                st.write(beschreibung)
                        else:
                            # Ohne Beschreibung → Normaler Text
                            st.markdown(f"**{counter}.** {titel}")
                        counter += 1
                    else:
                        # Legacy Format (String)
                        st.markdown(f"**{counter}.** {item}")
                        counter += 1
            else:
                st.info("Keine Unterlagen gefunden")
        
        with col2:
            st.subheader("⭐ Beurteilungskriterien")
            kriterien = data.get("beurteilungskriterien", [])
            
            if kriterien:
                for i, k in enumerate(kriterien, 1):
                    st.markdown(f"**{i}.** {k}")
            else:
                st.info("Keine Kriterien gefunden")
    
    # TAB 3: Teilnehmer & Kontakte
    with tab3:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("👥 Teilnehmende Teams")
            teilnehmende = data.get("teilnehmende", [])
            
            if teilnehmende:
                for i, name in enumerate(teilnehmende, 1):
                    st.markdown(f"""
                    <div class="success-box">
                        <strong>{i}.</strong> {name}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Keine Teilnehmer gefunden")
        
        with col2:
            st.subheader("📞 Kontaktpersonen")
            kontakte = data.get("kontakte", [])
            
            if kontakte:
                df = pd.DataFrame(kontakte)
                
                # Formatiere die Tabelle
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "name": st.column_config.TextColumn("Name", width="medium"),
                        "email": st.column_config.TextColumn("E-Mail", width="medium"),
                        "telefon": st.column_config.TextColumn("Telefon", width="small"),
                    }
                )
            else:
                st.info("Keine Kontakte gefunden")
    
    # TAB 4: Export
    with tab4:
        st.header("💾 Daten exportieren")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📄 JSON Export")
            st.write("Alle extrahierten Daten als JSON-Datei")
            
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 JSON herunterladen",
                data=json_str,
                file_name=f"{uploaded.name.replace('.pdf', '')}_extrahiert.json",
                mime="application/json",
                use_container_width=True
            )
            
            with st.expander("👁️ JSON Vorschau"):
                st.json(data)
        
        with col2:
            st.subheader("📊 Excel Export")
            st.write("Kontakte und Teilnehmer als Excel-Datei")
            
            if kontakte or teilnehmende:
                try:
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        if kontakte:
                            pd.DataFrame(kontakte).to_excel(writer, sheet_name='Kontakte', index=False)
                        if teilnehmende:
                            pd.DataFrame({'Teilnehmer': teilnehmende}).to_excel(writer, sheet_name='Teilnehmende', index=False)
                        
                        # Weitere Sheets
                        if data.get("einzureichende_unterlagen"):
                            pd.DataFrame({'Unterlagen': data["einzureichende_unterlagen"]}).to_excel(writer, sheet_name='Unterlagen', index=False)
                        if data.get("beurteilungskriterien"):
                            pd.DataFrame({'Kriterien': data["beurteilungskriterien"]}).to_excel(writer, sheet_name='Kriterien', index=False)
                    
                    output.seek(0)
                    st.download_button(
                        label="📥 Excel herunterladen",
                        data=output,
                        file_name=f"{uploaded.name.replace('.pdf', '')}_export.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                except ImportError:
                    st.warning("⚠️ Excel-Export benötigt 'openpyxl' Package")
                    st.code("pip install openpyxl")
            else:
                st.info("Keine exportierbaren Daten vorhanden")
    
    # TAB 5: Debug
    with tab5:
        st.header("🔍 Debug-Informationen")
        
        # Abgabetermin Debug
        if data.get("abgabetermin"):
            with st.expander("🗓️ Abgabetermin Details"):
                st.json(data["abgabetermin"])
        
        # Abgabeort Debug
        if data.get("abgabeort"):
            with st.expander("📍 Abgabeort Details"):
                st.json(data["abgabeort"])
        
        # Rohtext
        with st.expander("📄 Rohtext (erste 5000 Zeichen)"):
            st.text_area("Text", value=txt[:5000], height=300, disabled=True)
        
        # Alle Daten
        with st.expander("💾 Vollständige Daten (JSON)"):
            st.json(data)