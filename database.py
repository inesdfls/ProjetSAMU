import sqlite3
from datetime import datetime
import json
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    """Contexte manager pour la connexion à la base de données"""
    conn = sqlite3.connect('patients.db')
    conn.row_factory = sqlite3.Row  # Pour accéder aux colonnes par nom
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_database():
    """Initialise la base de données avec la table patients"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Création de la table avec la colonne status
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                symptoms TEXT NOT NULL,
                temperature REAL,
                heart_rate INTEGER,
                condition TEXT,
                urgency TEXT,
                status TEXT DEFAULT 'waiting',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("Base de données initialisée")

def load_patients_from_json():
    """Charge les patients existants depuis le JSON vers SQLite"""
    try:
        with open("patients.json", "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return
            
            # Charger les données JSON
            if content.startswith('['):
                patients = json.loads(content)
            else:
                patients = []
                for line in content.split('\n'):
                    line = line.strip()
                    if line:
                        try:
                            patients.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            
            # Insérer dans SQLite
            with get_db_connection() as conn:
                cursor = conn.cursor()
                for patient in patients:
                    cursor.execute('''
                        INSERT INTO patients (name, symptoms, temperature, heart_rate, condition, urgency, timestamp, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        patient.get('name'),
                        patient.get('symptoms'),
                        patient.get('temperature'),
                        patient.get('heart_rate'),
                        patient.get('condition'),
                        patient.get('urgency'),
                        patient.get('timestamp'),
                        'waiting'  # Statut par défaut
                    ))
                print(f"{len(patients)} patients migrés vers SQLite")
    except FileNotFoundError:
        print("Aucun fichier patients.json trouvé")
    except Exception as e:
        print(f"Erreur lors de la migration: {e}")

def save_patient_data(data):
    """Sauvegarde un nouveau patient dans la base SQLite"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO patients (name, symptoms, temperature, heart_rate, condition, urgency, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['name'],
            data['symptoms'],
            data['temperature'],
            data['heart_rate'],
            data['condition'],
            data['urgency'],
            data.get('timestamp', datetime.now().isoformat()),
            'waiting'  # Statut initial
        ))
        return cursor.lastrowid

def get_all_patients():
    """Récupère tous les patients"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM patients ORDER BY timestamp DESC')
        return cursor.fetchall()

def update_patient_status(patient_id, new_status):
    """Met à jour le statut d'un patient"""
    if new_status not in ['waiting', 'processing', 'done']:
        raise ValueError("Statut invalide. Doit être 'waiting', 'processing' ou 'done'")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE patients 
            SET status = ? 
            WHERE id = ?
        ''', (new_status, patient_id))
        return cursor.rowcount > 0

def get_patient_by_id(patient_id):
    """Récupère un patient par son ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
        return cursor.fetchone()