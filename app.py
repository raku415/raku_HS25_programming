import streamlit as st
import pandas as pd
from extractor.core import parse_text
from extractor.llm_validator import LLMValidator
import json
import re
import os

# =====================================================
# API-KEYS KONFIGURATION
# =====================================================
# WICHTIG: Trage KEINE API-Keys direkt hier ein wenn du das auf GitHub pushst!
# Nutze stattdessen:
# 1. Umgebungsvariablen (empfohlen): export OPENAI_API_KEY="..."
# 2. Eine .env Datei (wird von .gitignore ausgeschlossen)
# 3. Eingabe direkt in der Streamlit App (siehe Sidebar)
# =====================================================

st.set_page_config(
    page_title="Wettbewerb Extractor", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisiere Session State für Korrekturen
if 'corrected_data' not in st.session_state:
    st.session_state.corrected_data = {}

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
        background-color: #4870bf;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #8498c1;
        margin: 10px 0;
    }
    .success-box {
        background-color: #487a54;  /* Hellgrün - für Abgabeort */
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #718976;  /* Dunkelgrün */
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
    
    # LLM-Validierung Einstellungen
    st.markdown("### 🤖 LLM-Validierung")
    enable_validation = st.checkbox(
        "Validierung aktivieren",
        value=False,
        help="Nutzt OpenAI, Claude und Mistral zur Validierung der Extraktion"
    )
    
    if enable_validation:
        with st.expander("🔑 API Keys eingeben", expanded=True):
            st.info("💡 Tipp: Setze Umgebungsvariablen für automatisches Laden")
            st.caption("Gib mindestens einen API-Key ein:")
            
            openai_key = st.text_input(
                "OpenAI API Key",
                type="password",
                value=os.getenv("OPENAI_API_KEY", ""),
                help="Beginnt mit 'sk-proj-...' oder 'sk-...'"
            )
            
            claude_key = st.text_input(
                "Anthropic API Key",
                type="password",
                value=os.getenv("ANTHROPIC_API_KEY", ""),
                help="Beginnt mit 'sk-ant-...'"
            )
            
            mistral_key = st.text_input(
                "Mistral API Key",
                type="password",
                value=os.getenv("MISTRAL_API_KEY", ""),
                help="Von platform.mistral.ai"
            )
            
            if not any([openai_key, claude_key, mistral_key]):
                st.warning("⚠️ Mindestens ein API-Key erforderlich")
            else:
                active_llms = []
                if openai_key:
                    active_llms.append("OpenAI")
                if claude_key:
                    active_llms.append("Claude")
                if mistral_key:
                    active_llms.append("Mistral")
                st.success(f"✅ Aktive LLMs: {', '.join(active_llms)}")
    
    st.markdown("---")
    
    # Reset-Button (nur wenn Daten gecacht sind)
    if 'extracted_data' in st.session_state and st.session_state.extracted_data is not None:
        st.markdown("### 🔄 Neu extrahieren")
        if st.button("🔄 Cache löschen & neu starten", use_container_width=True):
            st.session_state.extracted_data = None
            st.session_state.corrected_data = {}
            st.session_state.current_file = None
            st.rerun()
        
        if st.session_state.corrected_data:
            st.caption(f"📝 {len(st.session_state.corrected_data)} Korrektur(en) gespeichert")
    
    st.markdown("---")
    st.markdown("### ℹ️ Über")
    st.caption("Dieses Tool extrahiert automatisch wichtige Informationen aus Architekturwettbewerbs-PDFs.")
    st.caption("Version 2.0 - mit LLM-Validierung")

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
    
    # Initialisiere Session State
    if 'corrected_data' not in st.session_state:
        st.session_state.corrected_data = {}
    
    if 'extracted_data' not in st.session_state:
        st.session_state.extracted_data = None
    
    if 'current_file' not in st.session_state:
        st.session_state.current_file = None
    
    # Prüfe ob es eine neue Datei ist
    file_changed = st.session_state.current_file != uploaded.name
    
    if file_changed:
        # Neue Datei → Reset und neu extrahieren
        st.session_state.corrected_data = {}
        st.session_state.extracted_data = None
        st.session_state.current_file = uploaded.name
    
    # Extrahiere nur wenn nötig (neue Datei oder noch keine Daten)
    if st.session_state.extracted_data is None:
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

            # Erstelle Validator wenn LLM-Validierung aktiviert
            validator = None
            if enable_validation:
                if any([openai_key, claude_key, mistral_key]):
                    validator = LLMValidator(
                        openai_key=openai_key if openai_key else None,
                        claude_key=claude_key if claude_key else None,
                    mistral_key=mistral_key if mistral_key else None
                )
                    st.info("🤖 LLM-Validierung wird durchgeführt... Dies kann 10-30 Sekunden dauern.")
            
            # Parse mit optionaler Validierung (NUR beim ersten Mal!)
            data = parse_text(txt, validate=enable_validation, validator=validator)
            
            # Speichere in Session State
            st.session_state.extracted_data = data
            st.success("✅ Extraktion abgeschlossen!")
    else:
        # Verwende gecachte Daten
        data = st.session_state.extracted_data.copy()
        st.info("ℹ️ Verwende gespeicherte Extraktion (keine erneute LLM-Validierung)")
    
    # Wende gespeicherte Korrekturen an (nach dem Laden)
    if st.session_state.corrected_data:
        for field, value in st.session_state.corrected_data.items():
            if field in data:
                data[field] = value
        
        # Zeige Korrektur-Status
        num_corrections = len(st.session_state.corrected_data)
        st.success(f"✅ {num_corrections} Korrektur(en) angewendet")
    
    
    # Tabs für verschiedene Bereiche
    if enable_validation and 'llm_validation' in data:
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Übersicht", 
            "📋 Unterlagen & Kriterien", 
            "👥 Teilnehmer & Kontakte",
            "🤖 LLM-Validierung",
            "💾 Export",
            "🔍 Debug"
        ])
    else:
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
        
        # Zeige kritische Korrekturvorschläge an (wenn LLM-Validierung aktiviert)
        if enable_validation and 'llm_validation' in data:
            validation = data.get('llm_validation', {})
            
            # Sammle alle kritischen Korrekturvorschläge
            critical_corrections = []
            
            for llm_name in ['claude', 'openai', 'mistral']:  # Priorisiere Claude
                llm_result = validation.get(llm_name)
                if llm_result and llm_result.get('status') == 'success':
                    # Prüfe jedes Feld
                    for field in ['besichtigung', 'abgabetermin', 'abgabeort']:
                        field_data = llm_result.get(field, {})
                        
                        if field_data.get('kritisch') and field_data.get('korrektur'):
                            critical_corrections.append({
                                'field': field,
                                'korrektur': field_data['korrektur'],
                                'kommentar': field_data.get('kommentar', ''),
                                'llm': llm_name,
                                'confidence': field_data.get('confidence', 0)
                            })
                    break  # Nutze nur das erste erfolgreiche LLM
            
            # Zeige Korrekturvorschläge an
            if critical_corrections:
                st.markdown("### ⚠️ Kritische Verbesserungsvorschläge")
                st.info("Die LLMs haben wichtige fehlende Informationen im PDF gefunden:")
                
                for correction in critical_corrections:
                    field_name_map = {
                        'besichtigung': '👁️ Besichtigung',
                        'abgabetermin': '🗓️ Abgabetermin',
                        'abgabeort': '📍 Abgabeort'
                    }
                    
                    field_display = field_name_map.get(correction['field'], correction['field'])
                    korrektur_data = correction['korrektur']
                    
                    with st.expander(f"✏️ {field_display} - {correction['kommentar']}", expanded=True):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            # Zeige die vorgeschlagene Korrektur
                            st.markdown("**Vorgeschlagene Ergänzung:**")
                            
                            if isinstance(korrektur_data, dict):
                                for key, value in korrektur_data.items():
                                    st.write(f"• **{key.capitalize()}**: {value}")
                            else:
                                st.write(korrektur_data)
                            
                            st.caption(f"Quelle: {correction['llm'].title()} (Confidence: {correction['confidence']}%)")
                        
                        with col2:
                            # Button zum Übernehmen
                            button_key = f"apply_{correction['field']}_{hash(str(korrektur_data))}"
                            
                            if st.button("✅ Übernehmen", key=button_key, use_container_width=True):
                                # Aktualisiere die Daten
                                if correction['field'] == 'besichtigung':
                                    if 'treffpunkt' in korrektur_data:
                                        if correction['field'] not in st.session_state.corrected_data:
                                            st.session_state.corrected_data[correction['field']] = data.get(correction['field'], {}).copy()
                                        st.session_state.corrected_data[correction['field']]['treffpunkt'] = korrektur_data['treffpunkt']
                                        data[correction['field']]['treffpunkt'] = korrektur_data['treffpunkt']
                                        st.success(f"✅ Treffpunkt übernommen: {korrektur_data['treffpunkt']}")
                                        st.rerun()
                                
                                elif correction['field'] == 'abgabeort':
                                    if 'adresse' in korrektur_data:
                                        st.session_state.corrected_data[correction['field']] = {
                                            'raw_block': korrektur_data['adresse'],
                                            'lines': [korrektur_data['adresse']],
                                            'source': 'llm_correction'
                                        }
                                        data[correction['field']] = st.session_state.corrected_data[correction['field']]
                                        st.success(f"✅ Abgabeort übernommen")
                                        st.rerun()
                
                st.markdown("---")
        
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
        
        # Besichtigungsdetails (wenn vorhanden)
        bes = data.get("besichtigung", {})
        if bes and (bes.get("treffpunkt") or bes.get("raw")):
            st.subheader("👁️ Besichtigungs-Details")
            col_bes1, col_bes2 = st.columns(2)
            
            with col_bes1:
                if bes.get("treffpunkt"):
                    st.markdown(f"""
                    <div class="info-box">
                        <strong>📍 Treffpunkt:</strong><br>
                        {bes.get("treffpunkt")}
                    </div>
                    """, unsafe_allow_html=True)
            
            with col_bes2:
                if bes.get("raw"):
                    st.markdown(f"""
                    <div class="info-box">
                        <strong>ℹ️ Weitere Informationen:</strong><br>
                        {bes.get("raw")}
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
        # Einleitungstext über voller Breite (falls vorhanden)
        unterlagen = data.get("einzureichende_unterlagen", [])
        
        einleitung_text = None
        start_index = 0
        
        # Prüfe ob das erste Item die Einleitung ist
        if unterlagen and len(unterlagen) > 0:
            first_item = unterlagen[0]
            if isinstance(first_item, dict):
                # Wenn erstes Item eine lange Beschreibung hat (> 200 Zeichen) und "Es werden" oder ähnliches enthält
                beschreibung = first_item.get("beschreibung", "")
                if beschreibung and len(beschreibung) > 200:
                    if re.search(r'(Es werden|Sämtliche|vorausgesetzt|einzureichen)', beschreibung, re.I):
                        # Kombiniere Titel + Beschreibung als Einleitung
                        titel = first_item.get("titel", "")
                        einleitung_text = f"{titel} {beschreibung}".strip()
                        start_index = 1  # Überspringe erstes Item bei der Anzeige
                elif first_item.get("typ") == "einleitung":
                    einleitung_text = first_item.get("beschreibung")
                    start_index = 1
        
        if einleitung_text:
            st.markdown(f"""
            <div style="background-color: #4B70BF; padding: 15px; border-radius: 8px; border-left: 4px solid #2498c1; margin: 10px 0; color: white;">
                {einleitung_text}
            </div>
            """, unsafe_allow_html=True)
            st.markdown("---")
        
        # Zwei Spalten für Unterlagen und Kriterien
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 Einzureichende Unterlagen")
            
            if unterlagen:
                counter = 1
                for idx, item in enumerate(unterlagen):
                    # Überspringe die Einleitung
                    if idx < start_index:
                        continue
                    
                    if isinstance(item, dict):
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
    
    # TAB 4: LLM-Validierung (nur wenn aktiviert)
    if enable_validation and 'llm_validation' in data:
        with tab4:
            st.header("🤖 LLM-Validierung & Smart-Korrektur")
            
            validation = data.get('llm_validation', {})
            
            # Sammle alle kritischen Korrekturen
            kritische_korrekturen = []
            for llm_name in ['openai', 'claude', 'mistral']:
                llm_result = validation.get(llm_name)
                if llm_result and llm_result.get('status') == 'success':
                    for field in ['abgabetermin', 'besichtigung', 'abgabeort', 'kontakte']:
                        if field in llm_result:
                            field_data = llm_result[field]
                            if field_data.get('kritisch') and field_data.get('korrektur'):
                                kritische_korrekturen.append({
                                    'llm': llm_name,
                                    'field': field,
                                    'korrektur': field_data['korrektur'],
                                    'kommentar': field_data.get('kommentar', '')
                                })
            
            # Zeige kritische Korrekturen prominent an
            if kritische_korrekturen:
                st.error("⚠️ **KRITISCHE FELDER GEFUNDEN** - Die LLMs haben wichtige fehlende Informationen erkannt!")
                
                for idx, korr in enumerate(kritische_korrekturen[:3]):  # Zeige max 3
                    field_name_map = {
                        'abgabetermin': '🗓️ Abgabetermin',
                        'besichtigung': '👁️ Besichtigung',
                        'abgabeort': '📍 Abgabeort',
                        'kontakte': '📞 Kontakte'
                    }
                    
                    with st.container():
                        st.markdown(f"### {field_name_map.get(korr['field'], korr['field'])}")
                        st.caption(f"🤖 Erkannt von: {korr['llm'].title()}")
                        
                        if isinstance(korr['korrektur'], dict):
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                st.info(f"💡 {korr['kommentar']}")
                                for key, value in korr['korrektur'].items():
                                    st.markdown(f"**{key.title()}:** {value}")
                            
                            with col2:
                                quick_apply_key = f"quick_apply_{korr['field']}_{idx}"
                                if st.button(
                                    "✅ Jetzt übernehmen",
                                    key=quick_apply_key,
                                    type="primary",
                                    use_container_width=True
                                ):
                                    # Übernehme Korrektur (gleiche Logik wie unten)
                                    if korr['field'] == 'besichtigung':
                                        corrected = data.get('besichtigung', {}).copy()
                                        if 'datum' in korr['korrektur']:
                                            corrected['iso'] = korr['korrektur']['datum']
                                        if 'zeit' in korr['korrektur']:
                                            corrected['time'] = korr['korrektur']['zeit']
                                        if 'treffpunkt' in korr['korrektur']:
                                            corrected['treffpunkt'] = korr['korrektur']['treffpunkt']
                                        st.session_state.corrected_data['besichtigung'] = corrected
                                    
                                    st.success("✅ Übernommen!")
                                    st.rerun()
                        
                        st.markdown("---")
            
            # Konsens-Übersicht
            if 'consensus' in validation and validation['consensus']:
                consensus = validation['consensus']
                
                st.subheader("📊 Konsens-Analyse")
                
                # Metriken
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    anzahl = consensus.get('anzahl_llms', 0)
                    st.markdown(f"""
                    <div class="main-metric">
                        <div class="metric-label">🤖 Anzahl LLMs</div>
                        <div class="metric-value">{anzahl}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    gesamt_conf = consensus.get('gesamt_confidence', 0)
                    st.markdown(f"""
                    <div class="main-metric">
                        <div class="metric-label">📈 Gesamt-Confidence</div>
                        <div class="metric-value">{gesamt_conf}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    qualitaet = consensus.get('qualitaet', 'Unbekannt')
                    st.markdown(f"""
                    <div class="main-metric">
                        <div class="metric-label">⭐ Qualität</div>
                        <div class="metric-value" style="font-size: 18px;">{qualitaet}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Confidence pro Feld
                st.subheader("📋 Confidence pro Feld")
                
                if 'durchschnittliche_confidence' in consensus:
                    conf_data = []
                    einigkeit_data = consensus.get('einigkeit', {})
                    
                    for field, conf in consensus['durchschnittliche_confidence'].items():
                        field_name_map = {
                            'abgabetermin': '🗓️ Abgabetermin',
                            'besichtigung': '👁️ Besichtigung',
                            'kontakte': '📞 Kontakte',
                            'einzureichende_unterlagen': '📋 Unterlagen',
                            'beurteilungskriterien': '⭐ Kriterien'
                        }
                        
                        conf_data.append({
                            'Feld': field_name_map.get(field, field),
                            'Confidence': f"{conf}%",
                            'Einigkeit': einigkeit_data.get(field, 'N/A')
                        })
                    
                    df_conf = pd.DataFrame(conf_data)
                    st.dataframe(df_conf, use_container_width=True, hide_index=True)
                
                # Kritische Unterschiede
                if consensus.get('kritische_unterschiede'):
                    st.markdown("---")
                    st.subheader("⚠️ Kritische Unterschiede")
                    st.warning("Die folgenden Felder haben eine niedrige Übereinstimmung zwischen den LLMs:")
                    
                    for diff in consensus['kritische_unterschiede']:
                        st.markdown(f"""
                        <div class="warning-box">
                            <strong>Feld:</strong> {diff['feld']}<br>
                            <strong>Einigkeit:</strong> {diff['einigkeit']}<br>
                            <strong>Empfehlung:</strong> {diff['empfehlung']}
                        </div>
                        """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Details pro LLM
            st.subheader("🔍 Details pro LLM")
            
            llm_tabs = []
            llm_data = {}
            
            if validation.get('openai') and validation['openai'].get('status') == 'success':
                llm_tabs.append("OpenAI GPT-4")
                llm_data['openai'] = validation['openai']
            
            if validation.get('claude') and validation['claude'].get('status') == 'success':
                llm_tabs.append("Claude Sonnet")
                llm_data['claude'] = validation['claude']
            
            if validation.get('mistral') and validation['mistral'].get('status') == 'success':
                llm_tabs.append("Mistral Large")
                llm_data['mistral'] = validation['mistral']
            
            if llm_tabs:
                llm_detail_tabs = st.tabs(llm_tabs)
                
                for idx, (llm_name, llm_result) in enumerate(llm_data.items()):
                    with llm_detail_tabs[idx]:
                        
                        # Gesamtbewertung
                        if 'gesamt_assessment' in llm_result:
                            assessment = llm_result['gesamt_assessment']
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Qualität", assessment.get('qualitaet', 'N/A'))
                            with col2:
                                st.metric("Ø Confidence", f"{assessment.get('confidence_durchschnitt', 0)}%")
                            
                            if assessment.get('empfehlung'):
                                st.info(f"**Empfehlung:** {assessment['empfehlung']}")
                            
                            if assessment.get('kritische_fehler'):
                                st.error(f"**Kritische Fehler:** {', '.join(assessment['kritische_fehler'])}")
                        
                        st.markdown("---")
                        
                        # Detaillierte Validierung pro Feld
                        fields_to_show = ['abgabetermin', 'besichtigung', 'kontakte', 
                                         'einzureichende_unterlagen', 'beurteilungskriterien']
                        
                        for field in fields_to_show:
                            if field in llm_result:
                                field_data = llm_result[field]
                                
                                field_name_map = {
                                    'abgabetermin': '🗓️ Abgabetermin',
                                    'besichtigung': '👁️ Besichtigung',
                                    'kontakte': '📞 Kontakte',
                                    'einzureichende_unterlagen': '📋 Unterlagen',
                                    'beurteilungskriterien': '⭐ Kriterien'
                                }
                                
                                with st.expander(field_name_map.get(field, field), expanded=False):
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        korrekt = field_data.get('korrekt', False)
                                        status_icon = "✅" if korrekt else "❌"
                                        st.write(f"**Status:** {status_icon} {'Korrekt' if korrekt else 'Fehlerhaft'}")
                                    
                                    with col2:
                                        confidence = field_data.get('confidence', 0)
                                        st.write(f"**Confidence:** {confidence}%")
                                    
                                    # Prüfe ob es ein kritisches Feld ist
                                    ist_kritisch = field_data.get('kritisch', False)
                                    if ist_kritisch:
                                        st.warning("⚠️ **KRITISCHES FELD** - Benötigt Aufmerksamkeit")
                                    
                                    if field_data.get('korrektur'):
                                        korrektur = field_data['korrektur']
                                        
                                        # Zeige Korrektur an
                                        if isinstance(korrektur, dict):
                                            st.warning("**📝 Korrekturvorschlag gefunden:**")
                                            
                                            # Formatiere die Korrektur schön
                                            for key, value in korrektur.items():
                                                st.markdown(f"- **{key.title()}:** {value}")
                                            
                                            # Button zum Übernehmen der Korrektur
                                            button_key = f"apply_{llm_name}_{field}_{idx}"
                                            if st.button(
                                                "✅ Korrektur übernehmen", 
                                                key=button_key,
                                                type="primary",
                                                help="Übernimmt die Korrektur in die extrahierten Daten"
                                            ):
                                                # Erstelle korrigierte Daten basierend auf dem Feld
                                                if field == 'besichtigung':
                                                    corrected = data.get('besichtigung', {}).copy()
                                                    if 'datum' in korrektur:
                                                        corrected['iso'] = korrektur['datum']
                                                    if 'zeit' in korrektur:
                                                        corrected['time'] = korrektur['zeit']
                                                    if 'treffpunkt' in korrektur:
                                                        corrected['treffpunkt'] = korrektur['treffpunkt']
                                                    st.session_state.corrected_data['besichtigung'] = corrected
                                                
                                                elif field == 'abgabetermin':
                                                    corrected = data.get('abgabetermin', {}).copy()
                                                    if 'datum' in korrektur:
                                                        corrected['iso'] = korrektur['datum']
                                                    if 'zeit' in korrektur:
                                                        corrected['time'] = korrektur['zeit']
                                                    st.session_state.corrected_data['abgabetermin'] = corrected
                                                
                                                elif field == 'abgabeort':
                                                    st.session_state.corrected_data['abgabeort'] = {
                                                        'raw_block': str(korrektur),
                                                        'source': 'llm_correction'
                                                    }
                                                
                                                st.success("✅ Korrektur übernommen! Scrolle nach oben zur Übersicht um die Änderung zu sehen.")
                                                st.rerun()
                                        else:
                                            st.warning(f"**Korrekturvorschlag:** {korrektur}")
                                    
                                    if field_data.get('fehlende'):
                                        fehlende = field_data['fehlende']
                                        # Konvertiere alle Items zu Strings
                                        if isinstance(fehlende, list):
                                            fehlende_str = ', '.join([str(item) for item in fehlende])
                                            st.info(f"**Fehlende Items:** {fehlende_str}")
                                        else:
                                            st.info(f"**Fehlende Items:** {str(fehlende)}")
                                    
                                    if field_data.get('kommentar'):
                                        st.caption(f"💬 {field_data['kommentar']}")
            else:
                st.info("Keine erfolgreichen LLM-Validierungen vorhanden")
            
            # Fehler-Anzeige
            errors = []
            for llm_name in ['openai', 'claude', 'mistral']:
                llm_result = validation.get(llm_name)
                if llm_result and llm_result.get('status') == 'failed':
                    error_type = llm_result.get('error_type', 'Unknown')
                    error_msg = llm_result.get('error', 'Unbekannter Fehler')
                    
                    # Spezifische Fehlermeldungen
                    if 'api_key' in error_msg.lower() or 'authentication' in error_msg.lower():
                        hint = "💡 Tipp: Überprüfe deinen API-Key"
                    elif 'quota' in error_msg.lower() or 'limit' in error_msg.lower():
                        hint = "💡 Tipp: API-Limit erreicht oder Guthaben aufgebraucht"
                    elif 'model' in error_msg.lower():
                        hint = "💡 Tipp: Modell nicht verfügbar für deinen Account"
                    else:
                        hint = ""
                    
                    errors.append({
                        'name': llm_name.title(),
                        'error': error_msg,
                        'type': error_type,
                        'hint': hint
                    })
            
            if errors:
                st.markdown("---")
                st.subheader("❌ Fehler bei der Validierung")
                
                for error_info in errors:
                    with st.expander(f"❌ {error_info['name']} - {error_info['type']}", expanded=True):
                        st.error(f"**Fehler:** {error_info['error']}")
                        if error_info['hint']:
                            st.info(error_info['hint'])
    
    # TAB 5 (oder 4 wenn keine Validierung): Export
    export_tab = tab5 if enable_validation and 'llm_validation' in data else tab4
    with export_tab:
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
    
    # TAB 6 (oder 5 wenn keine Validierung): Debug
    debug_tab = tab6 if enable_validation and 'llm_validation' in data else tab5
    with debug_tab:
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