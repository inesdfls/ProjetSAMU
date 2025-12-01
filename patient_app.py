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

# Import des fonctions SQLite
from database import get_all_patients, save_patient_data, update_patient_status

load_dotenv()
GLADIA_API_KEY = os.getenv("GLADIA_API_KEY")

# Configuration
st.set_page_config(
    page_title="SAMU - Système de Triage",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS simplifié
st.markdown("""
<style>
    .titre-principal {
        font-size: 2rem;
        font-weight: 600;
        color: #1E3A8A;
        margin-bottom: 1rem;
    }
    .titre-section {
        font-size: 1.25rem;
        font-weight: 500;
        color: #374151;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #E5E7EB;
    }
    .carte-patient {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .urgence-haute {
        color: #DC2626;
        font-weight: 600;
    }
    .urgence-moyenne {
        color: #D97706;
        font-weight: 600;
    }
    .urgence-basse {
        color: #059669;
        font-weight: 600;
    }
    .badge-statut {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    .statut-attente {
        background-color: #DBEAFE;
        color: #1E40AF;
    }
    .statut-traitement {
        background-color: #FEF3C7;
        color: #92400E;
    }
    .statut-termine {
        background-color: #D1FAE5;
        color: #065F46;
    }
</style>
""", unsafe_allow_html=True)

# Navigation
st.sidebar.markdown("## Navigation")
page = st.sidebar.radio(
    "Sélectionnez une page :",
    ["Formulaire Patient", "Tableau de Bord Médical"],
    label_visibility="collapsed"
)

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================
def charger_donnees_patients():
    """Charge les données des patients depuis SQLite"""
    try:
        patients = get_all_patients()
        return [dict(patient) for patient in patients]
    except Exception as e:
        st.error(f"Erreur de lecture de la base de données: {e}")
        return []

def transcrire_audio(filepath):
    """Transcrit l'audio en texte using Gladia API"""
    if not GLADIA_API_KEY:
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
                return ""
    except Exception:
        return ""

def valider_audio(audio_bytes):
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
    # Initialisation de la session state
    if 'texte_transcrit' not in st.session_state:
        st.session_state.texte_transcrit = ""
    if 'formulaire_soumis' not in st.session_state:
        st.session_state.formulaire_soumis = False
    if 'donnees_patient' not in st.session_state:
        st.session_state.donnees_patient = None
    
    # En-tête principal
    st.markdown('<div class="titre-principal">Formulaire Patient SAMU</div>', unsafe_allow_html=True)
    
    # Section 1: Transcription audio
    st.markdown('<div class="titre-section">1. Transcription Audio</div>', unsafe_allow_html=True)
    
    with st.container():
        col_audio1, col_audio2 = st.columns([3, 1])
        
        with col_audio1:
            fichier_audio = st.audio_input(
                "Enregistrez une description vocale des symptômes",
                key="entree_audio"
            )
        
        with col_audio2:
            st.write("")
            bouton_transcrire = st.button(
                "Transcrire",
                type="primary",
                use_container_width=True,
                disabled=not fichier_audio
            )
    
    # Gestion de la transcription
    if fichier_audio and bouton_transcrire:
        with st.spinner("Transcription en cours..."):
            est_valide, message = valider_audio(fichier_audio.getvalue())
            if est_valide:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    tmp.write(fichier_audio.read())
                    texte_symptomes = transcrire_audio(tmp.name)
                os.unlink(tmp.name)
                
                if texte_symptomes:
                    st.session_state.texte_transcrit = texte_symptomes
                    st.success("Transcription réussie")
                else:
                    st.warning("Impossible de transcrire l'audio")
    
    # Afficher la transcription si disponible
    if st.session_state.texte_transcrit:
        with st.expander("Transcription obtenue", expanded=False):
            st.write(st.session_state.texte_transcrit)
    
    # Section 2: Formulaire principal
    st.markdown('<div class="titre-section">2. Informations Patient</div>', unsafe_allow_html=True)
    
    if st.session_state.formulaire_soumis and st.session_state.donnees_patient:
        # Afficher les résultats après soumission
        donnees_patient = st.session_state.donnees_patient
        
        # Carte de résultats
        st.success("Patient enregistré avec succès")
        
        col_resultat1, col_resultat2 = st.columns(2)
        
        with col_resultat1:
            st.write(f"**ID Patient :** {donnees_patient['id']}")
            st.write(f"**Nom :** {donnees_patient['request'].name}")
            st.write(f"**Condition :** {donnees_patient['request'].prediagnosis.condition}")
            
            # Affichage urgence
            urgence = donnees_patient['request'].prediagnosis.urgencyLevel
            if urgence == "high":
                st.markdown(f'<span class="urgence-haute">**URGENCE : ÉLEVÉE**</span>', unsafe_allow_html=True)
            elif urgence == "medium":
                st.markdown(f'<span class="urgence-moyenne">**URGENCE : MOYENNE**</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span class="urgence-basse">**URGENCE : FAIBLE**</span>', unsafe_allow_html=True)
        
        with col_resultat2:
            st.write("**Paramètres vitaux :**")
            col_vitaux1, col_vitaux2 = st.columns(2)
            with col_vitaux1:
                st.write(f"**Température :** {donnees_patient['request'].temperature}°C")
            with col_vitaux2:
                st.write(f"**Fréquence cardiaque :** {donnees_patient['request'].heart_rate} bpm")
            
            st.write("**Symptômes :**")
            st.caption(donnees_patient['request'].prediagnosis.symptoms[:200] + "..." if len(donnees_patient['request'].prediagnosis.symptoms) > 200 else donnees_patient['request'].prediagnosis.symptoms)
        
        # Bouton pour nouveau patient
        if st.button("Nouveau Patient", type="primary", use_container_width=True):
            st.session_state.formulaire_soumis = False
            st.session_state.texte_transcrit = ""
            st.session_state.donnees_patient = None
            st.rerun()
    
    else:
        # Afficher le formulaire de saisie
        with st.form("formulaire_patient", clear_on_submit=True):
            # Informations de base
            col_info1, col_info2 = st.columns(2)
            
            with col_info1:
                nom = st.text_input(
                    "Nom du patient",
                    placeholder="Nom et prénom",
                    help="Nom complet du patient"
                )
            
            with col_info2:
                symptomes = st.text_area(
                    "Description des symptômes",
                    value=st.session_state.texte_transcrit,
                    placeholder="Décrivez les symptômes en détail",
                    height=100
                )
            
            # Paramètres vitaux
            st.write("**Paramètres vitaux**")
            col_vitaux1, col_vitaux2 = st.columns(2)
            
            with col_vitaux1:
                temperature = st.number_input(
                    "Température (°C)",
                    min_value=35.0,
                    max_value=42.0,
                    value=37.0,
                    step=0.1
                )
            
            with col_vitaux2:
                frequence_cardiaque = st.number_input(
                    "Fréquence cardiaque (bpm)",
                    min_value=40,
                    max_value=180,
                    value=75,
                    step=1
                )
            
            # Bouton de soumission
            bouton_soumettre = st.form_submit_button(
                "Générer le prédiagnostic",
                type="primary",
                use_container_width=True
            )
            
            if bouton_soumettre:
                if not nom or not symptomes:
                    st.error("Veuillez remplir le nom et les symptômes")
                else:
                    with st.spinner("Analyse en cours..."):
                        try:
                            prediagnostic = make_prediagnosis(symptomes)
                            
                            requete_patient = PatientRequest(
                                name=nom,
                                prediagnosis=prediagnostic,
                                temperature=temperature,
                                heart_rate=frequence_cardiaque
                            )
                            
                            donnees_patient = {
                                "name": nom,
                                "symptoms": symptomes,
                                "temperature": round(temperature, 1),
                                "heart_rate": frequence_cardiaque,
                                "condition": prediagnostic.condition,
                                "urgency": prediagnostic.urgencyLevel,
                                "timestamp": datetime.now().isoformat()
                            }
                            
                            id_patient = save_patient_data(donnees_patient)
                            
                            st.session_state.donnees_patient = {
                                "id": id_patient,
                                "request": requete_patient,
                                "data": donnees_patient
                            }
                            st.session_state.formulaire_soumis = True
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Erreur: {e}")

# PAGE 2: Tableau de Bord Médical
else:
    # En-tête du tableau de bord
    st.markdown('<div class="titre-principal">Tableau de Bord Médical SAMU</div>', unsafe_allow_html=True)
    
    try:
        patients = charger_donnees_patients()
        
        if not patients:
            st.info("Aucun patient enregistré")
        else:
            # Filtres
            st.markdown('<div class="titre-section">Filtres</div>', unsafe_allow_html=True)
            
            col_filtres1, col_filtres2, col_filtres3 = st.columns(3)
            
            with col_filtres1:
                filtre_urgence = st.selectbox(
                    "Niveau d'urgence",
                    ["Tous", "high", "medium", "low"]
                )
            
            with col_filtres2:
                filtre_statut = st.selectbox(
                    "Statut",
                    ["Tous", "waiting", "processing", "done"]
                )
            
            with col_filtres3:
                recherche_nom = st.text_input(
                    "Recherche par nom",
                    placeholder="Nom du patient"
                )
            
            # Statistiques
            st.markdown('<div class="titre-section">Statistiques</div>', unsafe_allow_html=True)
            
            col_stats1, col_stats2, col_stats3, col_stats4, col_stats5, col_stats6 = st.columns(6)
            
            total_patients = len(patients)
            urgence_haute = len([p for p in patients if p.get("urgency") == "high"])
            urgence_moyenne = len([p for p in patients if p.get("urgency") == "medium"])
            urgence_basse = len([p for p in patients if p.get("urgency") == "low"])
            statut_attente = len([p for p in patients if p.get("status") == "waiting"])
            statut_traitement = len([p for p in patients if p.get("status") == "processing"])
            statut_termine = len([p for p in patients if p.get("status") == "done"])
            
            with col_stats1:
                st.metric("Total", total_patients)
            
            with col_stats2:
                st.metric("Urgence Haute", urgence_haute)
            
            with col_stats3:
                st.metric("Urgence Moyenne", urgence_moyenne)
            
            with col_stats4:
                st.metric("Urgence Basse", urgence_basse)
            
            with col_stats5:
                st.metric("En attente", statut_attente)
            
            with col_stats6:
                st.metric("Terminés", statut_termine)
            
            # Application des filtres
            patients_filtres = patients.copy()
            
            if filtre_urgence != "Tous":
                patients_filtres = [p for p in patients_filtres if p.get("urgency") == filtre_urgence]
            
            if filtre_statut != "Tous":
                patients_filtres = [p for p in patients_filtres if p.get("status") == filtre_statut]
            
            if recherche_nom:
                patients_filtres = [p for p in patients_filtres if recherche_nom.lower() in p.get("name", "").lower()]
            
            # Liste des patients
            st.markdown(f'<div class="titre-section">Liste des Patients ({len(patients_filtres)})</div>', unsafe_allow_html=True)
            
            if not patients_filtres:
                st.info("Aucun patient ne correspond aux filtres")
            else:
                # Afficher chaque patient
                for patient in patients_filtres:
                    with st.container():
                        col_patient1, col_patient2, col_patient3 = st.columns([4, 2, 2])
                        
                        with col_patient1:
                            # Informations patient
                            st.write(f"**{patient.get('name', 'N/A')}** - ID: {patient.get('id')}")
                            st.caption(f"Symptômes: {patient.get('symptoms', 'N/A')[:100]}...")
                            
                            # Condition
                            st.write(f"Condition: {patient.get('condition', 'N/A')}")
                        
                        with col_patient2:
                            # Urgence et statut
                            urgence = patient.get('urgency', 'N/A')
                            if urgence == 'high':
                                st.markdown(f'<span class="urgence-haute">Urgence: Haute</span>', unsafe_allow_html=True)
                            elif urgence == 'medium':
                                st.markdown(f'<span class="urgence-moyenne">Urgence: Moyenne</span>', unsafe_allow_html=True)
                            elif urgence == 'low':
                                st.markdown(f'<span class="urgence-basse">Urgence: Basse</span>', unsafe_allow_html=True)
                            else:
                                st.write(f"Urgence: {urgence}")
                            
                            # Statut avec badge
                            statut = patient.get('status', 'waiting')
                            classe_statut = {
                                'waiting': 'statut-attente',
                                'processing': 'statut-traitement',
                                'done': 'statut-termine'
                            }.get(statut, '')
                            texte_statut = {
                                'waiting': 'En attente',
                                'processing': 'En traitement',
                                'done': 'Terminé'
                            }.get(statut, statut)
                            
                            st.markdown(f'<span class="badge-statut {classe_statut}">{texte_statut}</span>', unsafe_allow_html=True)
                        
                        with col_patient3:
                            # Paramètres vitaux
                            st.write(f"Température: {patient.get('temperature', 'N/A')}°C")
                            st.write(f"FC: {patient.get('heart_rate', 'N/A')} bpm")
                            
                            # Date
                            horodatage = patient.get('timestamp', '')
                            if horodatage:
                                try:
                                    date_obj = datetime.fromisoformat(horodatage.replace('Z', '+00:00'))
                                    st.caption(f"Date: {date_obj.strftime('%d/%m/%Y %H:%M')}")
                                except:
                                    st.caption(f"Date: {horodatage}")
                        
                        # Boutons d'action
                        id_patient = patient.get('id')
                        if id_patient:
                            col_actions1, col_actions2, col_actions3 = st.columns(3)
                            
                            with col_actions1:
                                if st.button("Traiter", key=f"traiter_{id_patient}", use_container_width=True):
                                    if update_patient_status(id_patient, 'processing'):
                                        st.success("Statut mis à jour")
                                        st.rerun()
                            
                            with col_actions2:
                                if st.button("Terminer", key=f"terminer_{id_patient}", use_container_width=True):
                                    if update_patient_status(id_patient, 'done'):
                                        st.success("Statut mis à jour")
                                        st.rerun()
                            
                            with col_actions3:
                                if st.button("Attente", key=f"attente_{id_patient}", use_container_width=True):
                                    if update_patient_status(id_patient, 'waiting'):
                                        st.success("Statut mis à jour")
                                        st.rerun()
                        
                        st.divider()
                
                # Export des données
                st.markdown('<div class="titre-section">Export des Données</div>', unsafe_allow_html=True)
                
                if st.button("Exporter en CSV", type="primary"):
                    donnees_tableau = []
                    for patient in patients_filtres:
                        horodatage = patient.get("timestamp", "")
                        try:
                            if horodatage:
                                date_obj = datetime.fromisoformat(horodatage.replace('Z', '+00:00'))
                                affichage_date = date_obj.strftime("%d/%m/%Y %H:%M")
                            else:
                                affichage_date = "N/A"
                        except:
                            affichage_date = horodatage
                        
                        donnees_tableau.append({
                            "ID": patient.get("id", "N/A"),
                            "Nom": patient.get("name", "N/A"),
                            "Symptômes": patient.get("symptoms", "N/A"),
                            "Condition": patient.get("condition", "N/A"),
                            "Urgence": patient.get("urgency", "N/A"),
                            "Statut": patient.get("status", "N/A"),
                            "Température": patient.get("temperature", "N/A"),
                            "FC": patient.get("heart_rate", "N/A"),
                            "Date": affichage_date
                        })
                    
                    df = pd.DataFrame(donnees_tableau)
                    csv = df.to_csv(index=False, encoding="utf-8-sig")
                    
                    st.download_button(
                        label="Télécharger CSV",
                        data=csv,
                        file_name=f"patients_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv"
                    )
    
    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {e}")
        st.info("Si le problème persiste, exécutez 'python init_db.py' pour initialiser la base de données.")