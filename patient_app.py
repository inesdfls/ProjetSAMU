import streamlit as st
from diagnosis import make_prediagnosis, make_prediagnosis_mock
from patient_dataclasses import PatientRequest

st.set_page_config(page_title="SAMU - Formulaire Patient")
st.title("Formulaire Patient - SAMU")

# Utiliser le mock pour tester sans LLM
USE_MOCK = True

# --- Formulaire ---
with st.form("patient_form"):
    name = st.text_input("Nom du patient")
    symptoms = st.text_area("Décrivez vos symptômes")
    temperature = st.number_input("Température (°C)", min_value=30.0, max_value=45.0, step=0.1)
    tension = st.text_input("Tension (ex: 120/80)")
    heart_rate = st.number_input("Fréquence cardiaque (bpm)", min_value=30, max_value=200)

    submitted = st.form_submit_button("Envoyer")

# --- Traitement ---
if submitted:
    if not name or not symptoms:
        st.warning("Merci de remplir le nom et les symptômes.")
    else:
        # Appel au LLM ou mock
        if USE_MOCK:
            prediag = make_prediagnosis_mock(symptoms)
        else:
            prediag = make_prediagnosis(symptoms)

        # Créer un objet PatientRequest
        patient_request = PatientRequest(
            name=name,
            prediagnosis=prediag,
            temperature=temperature,
            tension=tension,
            heart_rate=heart_rate
        )

        # Affichage du résultat
        st.success("Pré-diagnostic généré avec succès !")
        st.write("**Nom du patient :**", patient_request.name)
        st.write("**Symptômes :**", patient_request.prediagnosis.symptoms)
        st.write("**Condition :**", patient_request.prediagnosis.condition)
        st.write("**Urgence :**", patient_request.prediagnosis.urgencyLevel)
        st.write("**Température :**", patient_request.temperature)
        st.write("**Tension :**", patient_request.tension)
        st.write("**Fréquence cardiaque :**", patient_request.heart_rate)
