"""
model/config.py — Constantes globales del dominio.
"""
import os
import requests
import numpy as np
from utils import data_path

# ── API ───────────────────────────────────────────────────────────────────────
API_BASE_URL = "https://api-proyect-production.up.railway.app"

# Sesión HTTP compartida: reutiliza conexiones TCP/TLS al mismo host en vez de
# abrir un handshake nuevo por cada request (HTTP keep-alive + connection pool).
API_SESSION = requests.Session()
API_SESSION.headers.update({"Content-Type": "application/json"})

# ── Persistencia local (solo imágenes) ───────────────────────────────────────
DATASET_DIR   = data_path("dataset")

os.makedirs(DATASET_DIR, exist_ok=True)

# ── Análisis de emociones ─────────────────────────────────────────────────────
# TODO: umbral — evaluar si 0.5 s es suficiente o genera lag en sesiones largas
ANALYSIS_INTERVAL = 0.5          # segundos entre cada llamada a DeepFace  

# TODO: umbral — verificar impacto de resolución en precisión vs. rendimiento
ANALYSIS_SIZE     = (960, 540)   # resolución a la que se redimensiona antes de analizar  

EMOTION_KEYS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]

# TODO: MATRIZ DE CALIBRACIÓN/CONVERGENCIA — valores definidos manualmente; validar con datos empíricos reales
#       Cada fila i representa la distribución real de la emoción i cuando DeepFace predice esa clase.
#       Columnas: [angry, disgust, fear, happy, sad, surprise, neutral]
#  ang    dis    fear   hap    sad    sur    neu
CALIBRATION_MATRIX = np.array([
    [0.45, 0.08, 0.05, 0.00, 0.35, 0.02, 0.05],  # angry
    [0.25, 0.45, 0.05, 0.00, 0.15, 0.05, 0.05],  # disgust
    [0.05, 0.05, 0.45, 0.02, 0.15, 0.25, 0.03],  # fear
    [0.00, 0.00, 0.00, 0.95, 0.00, 0.03, 0.02],  # happy
    [0.12, 0.05, 0.05, 0.00, 0.72, 0.01, 0.05],  # sad
    [0.03, 0.01, 0.22, 0.05, 0.05, 0.60, 0.04],  # surprise
    [0.05, 0.02, 0.02, 0.05, 0.08, 0.03, 0.75],  # neutral
], dtype=np.float32)
