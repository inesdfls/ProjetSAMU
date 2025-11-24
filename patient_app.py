import streamlit as st
import json
import pandas as pd
import requests
from datetime import datetime
from diagnosis import make_prediagnosis
from patient_dataclasses import PatientRequest
import tempfile
import os
from dotenv import load_dotenv

load_dotenv()
GLADIA_API_KEY = os.getenv("GLADIA_API_KEY")

# Configuration
st.set_page_config(page_title="SAMU", layout="wide")

# Navigation
page = st.sidebar.selectbox("Navigation", ["Formulaire Patient", "Dashboard Medical"])

# Fonctions pour la gestion des données
def load_patients_data():
    """Charge les données des patients depuis le fichier JSON"""
    try:
        with open("patients.json", "r", encoding="utf-8") as f:
            content = f.read().strip()
            
            if not content:
                return []
                
            # Essayer de lire comme JSON array
            if content.startswith('['):
                return json.loads(content)
            # Sinon lire ligne par ligne (format JSONL)
            else:
                patients = []
                for line in content.split('\n'):
                    line = line.strip()
                    if line:
                        try:
                            patients.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
                return patients
                
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        st.error(f"Erreur de lecture du fichier JSON: {e}")
        return []

def save_patient_data(data):
    """Sauvegarde les données des patients dans le fichier JSON"""
    try:
        # Charger les données existantes
        existing_data = load_patients_data()
        
        # Ajouter les nouvelles données
        existing_data.append(data)
        
        # Sauvegarder en format JSON array
        with open("patients.json", "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde : {e}")

def transcribe_audio(filepath):
    """Transcrit l'audio en texte using Gladia API"""
    if not GLADIA_API_KEY:
        st.error("Clé API Gladia non configurée")
        return ""
    
    url = "https://api.gladia.io/audio/text/audio-transcription/"
    headers = {"x-gladia-key": GLADIA_API_KEY, "accept": "application/json"}

    try:
        with open(filepath, 'rb') as audio_file:
            files = {'audio': (os.path.basename(filepath), audio_file, 'audio/wav')}
            data = {'language_behaviour': 'automatic single language', 'toggle_diarization': 'false'}
            
            response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if "prediction" in result:
                    segments = result["prediction"]
                    if segments:
                        return " ".join([segment.get("transcription", "") for segment in segments]).strip()
                return result.get("text", "")
            else:
                st.error(f"Erreur API Gladia: {response.status_code}")
                return ""
    except Exception as e:
        st.error(f"Erreur lors de la transcription: {str(e)}")
        return ""

def validate_audio(audio_bytes):
    """Valide le fichier audio"""
    if not audio_bytes:
        return False, "Aucun audio détecté"
    if len(audio_bytes) < 1024:
        return False, "L'audio est trop court"
    if len(audio_bytes) > 10 * 1024 * 1024:
        return False, "L'audio est trop volumineux (max 10MB)"
    return True, "OK"

# PAGE 1: Formulaire Patient
if page == "Formulaire Patient":
    st.title("Formulaire Patient - SAMU")
    
    with st.form("patient_form"):
        name = st.text_input("Nom du patient")
        
        # Section enregistrement vocal
        st.subheader("Enregistrement vocal des symptômes")
        audio_file = st.audio_input("Appuyez pour enregistrer (format WAV recommandé)")
        
        symptoms_text = ""
        if audio_file:
            is_valid, msg = validate_audio(audio_file.getvalue())
            if not is_valid:
                st.error(f"Problème avec l'audio: {msg}")
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    tmp.write(audio_file.read())
                    
                with st.spinner("Transcription en cours..."):
                    symptoms_text = transcribe_audio(tmp.name)
                os.unlink(tmp.name)
                
                if symptoms_text:
                    st.success("✅ Transcription terminée")
                    st.text_area("Transcription obtenue", symptoms_text, height=100)

        # Saisie manuelle des symptômes
        symptoms = st.text_area("Décrivez vos symptômes", 
                               placeholder="Décrivez vos symptômes en détail...",
                               value=symptoms_text if symptoms_text else "")
        
        # Utiliser la transcription si disponible
        final_symptoms = symptoms_text if symptoms_text else symptoms

        col1, col2 = st.columns(2)
        with col1:
            temperature = st.number_input("Température (°C)", min_value=30.0, max_value=45.0, value=37.0, step=0.1)
        with col2:
            heart_rate = st.number_input("Fréquence cardiaque (bpm)", min_value=30, max_value=200, value=70)
        
        submitted = st.form_submit_button("Envoyer")

    if submitted:
        if not name or not final_symptoms:
            st.warning("Merci de remplir le nom et les symptômes.")
        else:
            try:
                prediag = make_prediagnosis(final_symptoms)

                patient_request = PatientRequest(
                    name=name,
                    prediagnosis=prediag,
                    temperature=temperature,
                    heart_rate=heart_rate
                )

                # Sauvegarde JSON
                patient_data = {
                    "name": name,
                    "symptoms": final_symptoms,
                    "temperature": round(temperature, 1),
                    "heart_rate": heart_rate,
                    "condition": prediag.condition,
                    "urgency": prediag.urgencyLevel,
                    "timestamp": datetime.now().isoformat()
                }
                
                save_patient_data(patient_data)

                # Affichage du résultat
                st.success("Pré-diagnostic généré avec succès !")
                st.write("### Résultats")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Nom :**", patient_request.name)
                    st.write("**Symptômes :**", patient_request.prediagnosis.symptoms)
                    st.write("**Condition :**", patient_request.prediagnosis.condition)
                with col2:
                    st.write("**Urgence :**", patient_request.prediagnosis.urgencyLevel)
                    st.write("**Température :**", patient_request.temperature)
                    st.write("**Fréquence cardiaque :**", patient_request.heart_rate)
                    
            except Exception as e:
                st.error(f"Erreur lors de la création du prédiagnostic: {e}")

# PAGE 2: Dashboard Medical
else:
    st.title("Dashboard Medical - SAMU")
    
    try:
        patients = load_patients_data()
        
        if not patients:
            st.warning("Aucun patient enregistré")
        else:
            # Filtre urgence
            urgency_filter = st.sidebar.selectbox("Filtrer par urgence", ["Tous", "high", "medium", "low"])
            
            # Recherche par nom
            search_name = st.sidebar.text_input("Rechercher par nom")
            
            # Statistiques
            col1, col2, col3, col4 = st.columns(4)
            total_patients = len(patients)
            high_urgency = len([p for p in patients if p.get("urgency") == "high"])
            medium_urgency = len([p for p in patients if p.get("urgency") == "medium"])
            low_urgency = len([p for p in patients if p.get("urgency") == "low"])
            
            with col1:
                st.metric("Total Patients", total_patients)
            with col2:
                st.metric("Urgences HIGH", high_urgency)
            with col3:
                st.metric("Urgences MEDIUM", medium_urgency)
            with col4:
                st.metric("Urgences LOW", low_urgency)
            
            # Appliquer filtres
            filtered_patients = patients.copy()
            
            if urgency_filter != "Tous":
                filtered_patients = [p for p in filtered_patients if p.get("urgency") == urgency_filter]
            
            if search_name:
                filtered_patients = [p for p in filtered_patients if search_name.lower() in p.get("name", "").lower()]
            
            st.subheader(f"Liste des Patients ({len(filtered_patients)})")
            
            # Tableau simple
            table_data = []
            for patient in filtered_patients:
                timestamp = patient.get("timestamp", "")
                try:
                    if timestamp:
                        date_obj = datetime.fromisoformat(timestamp)
                        date_display = date_obj.strftime("%d/%m/%Y %H:%M")
                    else:
                        date_display = "Non spécifié"
                except:
                    date_display = timestamp
                
                table_data.append({
                    "Nom": patient.get("name", "Non spécifié"),
                    "Symptômes": patient.get("symptoms", "Non spécifié"),
                    "Condition": patient.get("condition", "Non spécifié"),
                    "Urgence": patient.get("urgency", "Non spécifié"),
                    "Température": f"{patient.get('temperature', 'N/A')}°C",
                    "FC": f"{patient.get('heart_rate', 'N/A')} bpm",
                    "Date": date_display
                })
            
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Export CSV
            if st.button("Exporter en CSV"):
                csv = df.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    label="Télécharger CSV",
                    data=csv,
                    file_name=f"patients_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
                
    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {e}")
        st.info("Si le problème persiste, essayez de supprimer le fichier patients.json pour recommencer.")