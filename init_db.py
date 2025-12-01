from database import init_database, load_patients_from_json

if __name__ == "__main__":
    print("Initialisation de la base de données...")
    init_database()
    print("Migration des données JSON vers SQLite...")
    load_patients_from_json()
    print("Base de données prête !")