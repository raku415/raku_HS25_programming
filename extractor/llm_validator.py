# extractor/llm_validator.py
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

class LLMValidator:
    """
    Validiert extrahierte Wettbewerbsdaten mit mehreren LLMs.
    Unterstützt OpenAI, Claude (Anthropic) und Mistral.
    """
    
    def __init__(self, openai_key: str = None, claude_key: str = None, mistral_key: str = None):
        """
        Initialisiert den Validator mit API-Keys.
        
        Args:
            openai_key: OpenAI API Key
            claude_key: Anthropic API Key
            mistral_key: Mistral API Key
        """
        self.openai_key = openai_key or os.getenv("OPENAI_API_KEY")
        self.claude_key = claude_key or os.getenv("ANTHROPIC_API_KEY")
        self.mistral_key = mistral_key or os.getenv("MISTRAL_API_KEY")
        
        # Initialisiere Clients
        self.openai_client = None
        self.claude_client = None
        self.mistral_client = None
        
        if self.openai_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.openai_key)
            except ImportError:
                print("⚠️ OpenAI package nicht installiert. Installiere mit: pip install openai")
        
        if self.claude_key:
            try:
                from anthropic import Anthropic
                self.claude_client = Anthropic(api_key=self.claude_key)
            except ImportError:
                print("⚠️ Anthropic package nicht installiert. Installiere mit: pip install anthropic")
        
        if self.mistral_key:
            try:
                from mistralai import Mistral
                self.mistral_client = Mistral(api_key=self.mistral_key)
            except ImportError:
                print("⚠️ Mistral package nicht installiert. Installiere mit: pip install mistralai")
    
    def _create_validation_prompt(self, extracted_data: Dict[str, Any], raw_text: str) -> str:
        """
        Erstellt den Validierungs-Prompt für die LLMs.
        
        Args:
            extracted_data: Die mit Regex extrahierten Daten
            raw_text: Der Originaltext aus dem PDF (gekürzt für Context)
        
        Returns:
            Der formatierte Prompt
        """
        # Kürze den Text auf max 8000 Zeichen für bessere Performance
        text_snippet = raw_text[:8000] if len(raw_text) > 8000 else raw_text
        
        prompt = f"""Du bist ein Experte für Architekturwettbewerbe in der Schweiz. 
Deine Aufgabe ist es, automatisch extrahierte Daten aus einem Wettbewerbsdokument zu validieren.

EXTRAHIERTE DATEN (mit Regex):
{json.dumps(extracted_data, ensure_ascii=False, indent=2)}

ORIGINAL-TEXT (Auszug):
{text_snippet}

AUFGABE:
Überprüfe die extrahierten Daten auf Richtigkeit und Vollständigkeit. Gib für jedes Feld an:
1. Ist die Information korrekt? (ja/nein/unklar)
2. Confidence Score (0-100%)
3. Korrekturvorschlag (falls nötig)
4. Fehlende Informationen, die im Text vorhanden sind

Antworte im folgenden JSON-Format:
{{
  "abgabetermin": {{
    "korrekt": true/false,
    "confidence": 95,
    "korrektur": "2024-12-31 14:00" oder null,
    "kommentar": "Optionaler Kommentar"
  }},
  "besichtigung": {{
    "korrekt": true/false,
    "confidence": 80,
    "korrektur": null,
    "kommentar": ""
  }},
  "kontakte": {{
    "korrekt": true/false,
    "confidence": 90,
    "fehlende": ["name@example.ch"],
    "kommentar": ""
  }},
  "einzureichende_unterlagen": {{
    "korrekt": true/false,
    "confidence": 85,
    "fehlende": ["Modell 1:200"],
    "kommentar": ""
  }},
  "beurteilungskriterien": {{
    "korrekt": true/false,
    "confidence": 75,
    "fehlende": [],
    "kommentar": ""
  }},
  "gesamt_assessment": {{
    "qualitaet": "gut/mittel/schlecht",
    "confidence_durchschnitt": 85,
    "kritische_fehler": [],
    "empfehlung": "Kurze Zusammenfassung"
  }}
}}

Antworte NUR mit dem JSON-Objekt, ohne zusätzlichen Text."""
        
        return prompt
    
    def validate_with_openai(self, extracted_data: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
        """
        Validiert mit OpenAI GPT-4.
        
        Args:
            extracted_data: Extrahierte Daten
            raw_text: Originaltext
        
        Returns:
            Validierungsergebnis
        """
        if not self.openai_client:
            return {"error": "OpenAI client nicht verfügbar", "status": "failed"}
        
        try:
            prompt = self._create_validation_prompt(extracted_data, raw_text)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # Verwende GPT-4o (neuestes Modell)
                messages=[
                    {"role": "system", "content": "Du bist ein Experte für die Validierung von Wettbewerbsdaten. Antworte immer mit validen JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Niedrige Temperature für konsistente Ergebnisse
                response_format={"type": "json_object"}  # Erzwinge JSON-Antwort
            )
            
            result = json.loads(response.choices[0].message.content)
            result["status"] = "success"
            result["model"] = "gpt-4o"
            result["timestamp"] = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "status": "failed",
                "model": "gpt-4o"
            }
    
    def validate_with_claude(self, extracted_data: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
        """
        Validiert mit Anthropic Claude.
        
        Args:
            extracted_data: Extrahierte Daten
            raw_text: Originaltext
        
        Returns:
            Validierungsergebnis
        """
        if not self.claude_client:
            return {"error": "Claude client nicht verfügbar", "status": "failed"}
        
        try:
            prompt = self._create_validation_prompt(extracted_data, raw_text)
            
            message = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",  # Neuestes Sonnet Modell
                max_tokens=4096,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extrahiere JSON aus der Antwort
            content = message.content[0].text
            
            # Versuche JSON zu parsen (Claude könnte Markdown-Blöcke verwenden)
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content
            
            result = json.loads(json_str)
            result["status"] = "success"
            result["model"] = "claude-sonnet-4"
            result["timestamp"] = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "status": "failed",
                "model": "claude-sonnet-4"
            }
    
    def validate_with_mistral(self, extracted_data: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
        """
        Validiert mit Mistral AI.
        
        Args:
            extracted_data: Extrahierte Daten
            raw_text: Originaltext
        
        Returns:
            Validierungsergebnis
        """
        if not self.mistral_client:
            return {"error": "Mistral client nicht verfügbar", "status": "failed"}
        
        try:
            prompt = self._create_validation_prompt(extracted_data, raw_text)
            
            response = self.mistral_client.chat.complete(
                model="mistral-large-latest",
                messages=[
                    {
                        "role": "system",
                        "content": "Du bist ein Experte für die Validierung von Wettbewerbsdaten. Antworte immer mit validen JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["status"] = "success"
            result["model"] = "mistral-large"
            result["timestamp"] = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "status": "failed",
                "model": "mistral-large"
            }
    
    def validate_all(self, extracted_data: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
        """
        Führt Validierung mit allen verfügbaren LLMs durch.
        
        Args:
            extracted_data: Extrahierte Daten
            raw_text: Originaltext
        
        Returns:
            Zusammengefasstes Validierungsergebnis von allen LLMs
        """
        results = {
            "openai": None,
            "claude": None,
            "mistral": None,
            "consensus": None
        }
        
        # Validiere mit jedem verfügbaren LLM
        if self.openai_client:
            print("🔄 Validiere mit OpenAI...")
            results["openai"] = self.validate_with_openai(extracted_data, raw_text)
        
        if self.claude_client:
            print("🔄 Validiere mit Claude...")
            results["claude"] = self.validate_with_claude(extracted_data, raw_text)
        
        if self.mistral_client:
            print("🔄 Validiere mit Mistral...")
            results["mistral"] = self.validate_with_mistral(extracted_data, raw_text)
        
        # Erstelle Konsens-Analyse
        results["consensus"] = self._analyze_consensus(results)
        
        return results
    
    def _analyze_consensus(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analysiert die Ergebnisse aller LLMs und findet Konsens.
        
        Args:
            results: Dictionary mit Ergebnissen von allen LLMs
        
        Returns:
            Konsens-Analyse
        """
        successful_results = [
            r for r in [results.get("openai"), results.get("claude"), results.get("mistral")]
            if r and r.get("status") == "success"
        ]
        
        if not successful_results:
            return {
                "status": "no_consensus",
                "reason": "Keine erfolgreichen Validierungen"
            }
        
        # Berechne durchschnittliche Confidence-Scores
        consensus = {
            "anzahl_llms": len(successful_results),
            "durchschnittliche_confidence": {},
            "einigkeit": {},
            "kritische_unterschiede": []
        }
        
        # Sammle Confidence-Scores für jedes Feld
        fields = ["abgabetermin", "besichtigung", "kontakte", "einzureichende_unterlagen", "beurteilungskriterien"]
        
        for field in fields:
            confidences = []
            korrekt_votes = []
            
            for result in successful_results:
                if field in result:
                    field_data = result[field]
                    if isinstance(field_data, dict):
                        if "confidence" in field_data:
                            confidences.append(field_data["confidence"])
                        if "korrekt" in field_data:
                            korrekt_votes.append(field_data["korrekt"])
            
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
                consensus["durchschnittliche_confidence"][field] = round(avg_confidence, 1)
                
                # Prüfe Einigkeit
                if korrekt_votes:
                    agreement = sum(1 for v in korrekt_votes if v) / len(korrekt_votes)
                    consensus["einigkeit"][field] = f"{int(agreement * 100)}%"
                    
                    # Markiere kritische Unterschiede (< 50% Einigkeit)
                    if agreement < 0.5:
                        consensus["kritische_unterschiede"].append({
                            "feld": field,
                            "einigkeit": f"{int(agreement * 100)}%",
                            "empfehlung": "Manuelle Überprüfung erforderlich"
                        })
        
        # Gesamtbewertung
        if consensus["durchschnittliche_confidence"]:
            overall_confidence = sum(consensus["durchschnittliche_confidence"].values()) / len(consensus["durchschnittliche_confidence"])
            consensus["gesamt_confidence"] = round(overall_confidence, 1)
            
            if overall_confidence >= 85:
                consensus["qualitaet"] = "Sehr gut - hohe Zuverlässigkeit"
            elif overall_confidence >= 70:
                consensus["qualitaet"] = "Gut - meistens zuverlässig"
            elif overall_confidence >= 50:
                consensus["qualitaet"] = "Mittel - Überprüfung empfohlen"
            else:
                consensus["qualitaet"] = "Niedrig - manuelle Prüfung erforderlich"
        
        return consensus


def get_validator_with_env() -> Optional[LLMValidator]:
    """
    Erstellt einen Validator mit API-Keys aus Umgebungsvariablen.
    
    Returns:
        LLMValidator-Instanz oder None wenn keine Keys verfügbar
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    claude_key = os.getenv("ANTHROPIC_API_KEY")
    mistral_key = os.getenv("MISTRAL_API_KEY")
    
    if not any([openai_key, claude_key, mistral_key]):
        return None
    
    return LLMValidator(
        openai_key=openai_key,
        claude_key=claude_key,
        mistral_key=mistral_key
    )
