import requests
from dataclasses import dataclass
from dotenv import load_dotenv
import os

# Charger les variables d'environnement
load_dotenv()
API_KEY = os.getenv("MISTRAL_API_KEY")

# Vérification API KEY
if not API_KEY:
    raise ValueError("ERREUR : la clé API Mistral n'est pas trouvée dans le fichier .env")

@dataclass
class PreDiagnosis:
    condition: str
    urgencyLevel: str 
    symptoms: str

# Endpoint Mistral
URL = "https://api.mistral.ai/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ----
# LLM
# ----
def make_prediagnosis(symptoms: str) -> PreDiagnosis:
    """Appelle le LLM Mistral et retourne un prédiagnostic structuré."""

    messages = [
        {"role": "system", "content": (
            "Tu es un assistant médical professionnel. "
            "Tu dois analyser les symptômes décrits et fournir :\n"
            "1. Un prédiagnostic médical plausible\n"
            "2. Un niveau d'urgence (low/medium/high)\n"
            "\n"
            "Critères d'urgence :\n"
            "- HIGH : symptômes potentiellement graves (douleur thoracique, difficultés respiratoires, etc.)\n"
            "- MEDIUM : symptômes nécessitant une consultation mais pas d'urgence vitale\n"
            "- LOW : symptômes bénins pouvant attendre une consultation normale\n"
            "\n"
            "Réponds UNIQUEMENT au format exact suivant :\n"
            "Condition: [ton diagnostic ici]\n"
            "Urgency: [low|medium|high]"
        )},
        {"role": "user", "content": (
            f"Patient présente les symptômes suivants : {symptoms}.\n"
            "Fournis un prédiagnostic et le niveau d'urgence."
        )}
    ]

    data = {
        "model": "mistral-tiny-latest",
        "messages": messages,
        "max_tokens": 200,
        "temperature": 0.3
    }

    # --- Appel API ---
    response = requests.post(URL, headers=HEADERS, json=data)

    # --- Gestion des erreurs ---
    if response.status_code != 200:
        print("ERREUR API :", response.status_code, response.text)
        return PreDiagnosis(
            condition="Erreur API",
            urgencyLevel="medium",
            symptoms=symptoms
        )

    # --- Lecture réponse ---
    result = response.json()
    text = result["choices"][0]["message"]["content"].strip()

    print("Réponse brute LLM :", text)

    # --- Parsing ---
    condition = ""
    urgency = "medium"

    if "Condition:" in text and "Urgency:" in text:
        try:
            parts = text.split("Condition:")[1].split("Urgency:")
            condition = parts[0].strip()
            urgency = parts[1].strip().split("\n")[0].strip().lower()
        except Exception as e:
            print("Erreur parsing :", e)
            condition = text
    else:
        condition = text

    return PreDiagnosis(
        condition=condition,
        urgencyLevel=urgency,
        symptoms=symptoms
    )


# Test manuel
if __name__ == "__main__":
    test = make_prediagnosis("fièvre, toux, fatigue")
    print("Prédiagnostic :", test)