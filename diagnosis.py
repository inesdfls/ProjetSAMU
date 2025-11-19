# diagnosis.py

import requests
from dataclasses import dataclass
from dotenv import load_dotenv
import os

# Charger les variables d'environnement
load_dotenv()
API_KEY = os.getenv("MISTRAL_API_KEY")

@dataclass
class PreDiagnosis:
    condition: str
    urgencyLevel: str  # "low", "medium", "high"
    symptoms: str

URL = "https://api.mistral.ai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# -----------------------
# Version réelle LLM
# -----------------------
def make_prediagnosis(symptoms: str) -> PreDiagnosis:
    messages = [
        {"role": "system", "content": "Tu es un assistant médical."},
        {"role": "user", "content": (
            f"Je ressens ces symptômes : {symptoms}.\n"
            "Donne un prédiagnostic et un niveau d'urgence.\n"
            "Répond exactement au format :\n"
            "Condition: <diagnostic>\n"
            "Urgency: <low|medium|high>"
        )}
    ]

    data = {
        "model": "mistral-small-latest",
        "messages": messages,
        "max_tokens": 200
    }

    response = requests.post(URL, headers=HEADERS, json=data)

    if response.status_code == 429:
        print("⚠️ Quota API dépassé, utilisez la version mock")
        return make_prediagnosis_mock(symptoms)

    if response.status_code != 200:
        print("Erreur API :", response.status_code, response.text)
        return PreDiagnosis(condition="Erreur API", urgencyLevel="medium", symptoms=symptoms)

    result = response.json()
    text = result["choices"][0]["message"]["content"].strip()
    print("Réponse brute LLM :", text)

    # Parsing robuste
    condition = ""
    urgency = "medium"
    if "Condition:" in text and "Urgency:" in text:
        try:
            parts = text.split("Condition:")[1].split("Urgency:")
            condition = parts[0].strip()
            urgency = parts[1].strip().split("\n")[0].strip()
        except Exception as e:
            print("Erreur parsing :", e)
            condition = text
    else:
        condition = text

    return PreDiagnosis(condition=condition, urgencyLevel=urgency, symptoms=symptoms)

# -----------------------
# Version mock pour tester sans LLM
# -----------------------
def make_prediagnosis_mock(symptoms: str) -> PreDiagnosis:
    print("⚠️ Mock : utilisation d'un prédiagnostic simulé")
    return PreDiagnosis(
        condition="Infection virale simulée",
        urgencyLevel="low",
        symptoms=symptoms
    )

# Test rapide
if __name__ == "__main__":
    pred = make_prediagnosis_mock("fièvre, toux, fatigue")
    print("Prédiagnostic :", pred)
