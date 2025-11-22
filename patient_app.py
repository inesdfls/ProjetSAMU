import streamlit as st
import json
import pandas as pd
import requests
import os
from datetime import datetime
from diagnosis import make_prediagnosis
from patient_dataclasses import PatientRequest

# Configuration
st.set_page_config(page_title="SAMU", layout="wide")

# Navigation
page = st.sidebar.selectbox("Navigation", ["Formulaire Patient", "Dashboard Medical"])

# Fonction pour charger les patients
def load_patients_data():
    try:
        with open("patients.json", "r", encoding="utf-8") as f:
            lines = f.readlines()
            patients = [json.loads(line) for line in lines if line.strip()]
        return patients
    except FileNotFoundError:
        return []

# Fonction pour transcrire l'audio
def transcribe_audio(audio_file):
    api_key = os.getenv("GLADIA_API_KEY")
    if not api_key:
        return "Erreur: Cle API Gladia non configuree"
        
    url = "https://api.gladia.io/v2/transcription/"
    
    # Lire les bytes du fichier audio
    audio_bytes = audio_file.getvalue()
    
    headers = {
        "x-gladia-key": api_key
    }
    
    # Premier appel pour uploader l'audio
    files = {
        "audio": (audio_file.name, audio_bytes, "audio/wav")
    }
    
    try:
        # Upload de l'audio
        upload_response = requests.post(url, files=files, headers=headers)
        
        if upload_response.status_code == 200:
            result = upload_response.json()
            transcription = result.get("prediction", "")
            if transcription:
                return transcription
            else:
                return "Erreur: Transcription vide"
        else:
            return f"Erreur API: {upload_response.status_code}"
            
    except Exception as e:
        return f"Erreur: {str(e)}"

# PAGE 1: Formulaire Patient
if page == "Formulaire Patient":
    st.title("Formulaire Patient - SAMU")
    
    # Initialisation de l'état de transcription
    if 'transcribed_text' not in st.session_state:
        st.session_state.transcribed_text = ""
    
    # Enregistrement vocal
    audio_file = st.audio_input("Enregistrez vos symptomes")
    
    # Bouton de transcription
    if audio_file:
        if st.button("Transcrire l'audio"):
            with st.spinner("Transcription en cours..."):
                transcribed_text = transcribe_audio(audio_file)
                st.session_state.transcribed_text = transcribed_text
    
    # Afficher la transcription si elle existe
    if st.session_state.transcribed_text:
        st.text_area("Transcription", st.session_state.transcribed_text, key="transcription_display")
    
    # Formulaire principal
    with st.form("patient_form"):
        name = st.text_input("Nom du patient")
        
        # Champ symptomes pre-rempli si transcription
        symptoms = st.text_area("Decrivez vos symptomes", value=st.session_state.transcribed_text)
        
        temperature = st.number_input("Temperature (°C)", min_value=30.0, max_value=45.0, step=0.1)
        heart_rate = st.number_input("Frequence cardiaque (bpm)", min_value=30, max_value=200)
        
        submitted = st.form_submit_button("Envoyer")

    if submitted:
        if not name or not symptoms:
            st.warning("Merci de remplir le nom et les symptomes.")
        else:
            prediag = make_prediagnosis(symptoms)

            patient_request = PatientRequest(
                name=name,
                prediagnosis=prediag,
                temperature=temperature,
                heart_rate=heart_rate
            )

            # Sauvegarde JSON
            patient_data = {
                "name": name,
                "symptoms": symptoms,
                "temperature": temperature,
                "heart_rate": heart_rate,
                "condition": prediag.condition,
                "urgency": prediag.urgencyLevel,
                "timestamp": datetime.now().isoformat()
            }
            
            with open("patients.json", "a", encoding="utf-8") as f:
                f.write(json.dumps(patient_data, ensure_ascii=False) + "\n")

            # Affichage du resultat
            st.success("Pre-diagnostic genere avec succes !")
            st.write("### Resultats")
            st.write("**Nom :**", patient_request.name)
            st.write("**Symptomes :**", patient_request.prediagnosis.symptoms)
            st.write("**Condition :**", patient_request.prediagnosis.condition)
            st.write("**Urgence :**", patient_request.prediagnosis.urgencyLevel)
            st.write("**Temperature :**", patient_request.temperature)
            st.write("**Frequence cardiaque :**", patient_request.heart_rate)
            
            # Reinitialiser la transcription apres envoi
            st.session_state.transcribed_text = ""

# PAGE 2: Dashboard Medical
else:
    st.title("Dashboard Medical - SAMU")
    
    patients = load_patients_data()
    
    if not patients:
        st.warning("Aucun patient enregistre")
    else:
        # Filtre urgence
        urgency_filter = st.selectbox("Filtrer par urgence", ["Tous", "high", "medium", "low"])
        
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
        
        # Appliquer filtre
        if urgency_filter != "Tous":
            filtered_patients = [p for p in patients if p.get("urgency") == urgency_filter]
        else:
            filtered_patients = patients
        
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
                    date_display = "Non specifie"
            except:
                date_display = timestamp
            
            table_data.append({
                "Nom": patient.get("name", "Non specifie"),
                "Symptomes": patient.get("symptoms", "Non specifie"),
                "Condition": patient.get("condition", "Non specifie"),
                "Urgence": patient.get("urgency", "Non specifie"),
                "Temperature": patient.get("temperature", "N/A"),
                "FC": patient.get("heart_rate", "N/A"),
                "Date": date_display
            })
        
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)