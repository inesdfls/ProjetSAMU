# ProjetSAMU

# SAMU Triage System

Système de triage médical utilisant l'IA pour analyser les symptômes et gérer la file d'attente aux urgences.

## Fonctionnalités

**Formulaire Patient**
- Transcription audio des symptômes (API Gladia)
- Saisie des informations patient
- Prédiagnostic par IA (Mistral AI)
- Évaluation du niveau d'urgence (low/medium/high)

**Tableau de Bord Médical**
- Vue d'ensemble des patients
- Filtres par urgence et statut
- Statistiques en temps réel
- Gestion des statuts (waiting/processing/done)
- Export CSV des données

## Installation

```bash
# Cloner le dépôt
git clone https://github.com/votre-organisation/samu-triage-system.git
cd samu-triage-system

# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install streamlit requests python-dotenv pandas

# Configurer les clés API
cp .env.example .env
# Éditer .env avec vos clés MISTRAL_API_KEY et GLADIA_API_KEY

# Initialiser la base de données
python init_db.py

# Lancer l'application
streamlit run patient_app.py
```

## Structure du Projet

```
samu-triage-system/
├── patient_app.py          # Interface principale
├── database.py             # Gestion base de données SQLite
├── diagnosis.py            # Analyse IA (Mistral)
├── patient_dataclasses.py  # Structures de données
├── init_db.py              # Initialisation BDD
├── patients.db             # Base de données SQLite
└── .env                    # Configuration clés API
```

## Base de Données

Table `patients` :
- id (INTEGER) : Identifiant unique
- name (TEXT) : Nom du patient
- symptoms (TEXT) : Symptômes décrits
- temperature (REAL) : Température
- heart_rate (INTEGER) : Fréquence cardiaque
- condition (TEXT) : Diagnostic suggéré
- urgency (TEXT) : Niveau d'urgence
- status (TEXT) : Statut (waiting/processing/done)
- timestamp (DATETIME) : Date d'enregistrement

## Configuration

Fichier `.env` :
```
MISTRAL_API_KEY=votre_cle_api
GLADIA_API_KEY=votre_cle_api
```

## Utilisation

1. **Enregistrement** : Description vocale des symptômes
2. **Formulaire** : Saisie des informations complémentaires
3. **Diagnostic** : Analyse automatique par l'IA
4. **Suivi** : Gestion des patients dans le tableau de bord
5. **Export** : Téléchargement des données au format CSV
