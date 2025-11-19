from dataclasses import dataclass
from diagnosis import PreDiagnosis

@dataclass
class PatientRequest:
    name: str
    prediagnosis: PreDiagnosis
    temperature: float
    tension: str
    heart_rate: int
