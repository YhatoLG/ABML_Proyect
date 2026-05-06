"""
model/emotion_analyzer.py — Wrapper de DeepFace con corrección por calibración.

Uso:
    emotion, prob = analyze_emotion(bgr_frame)
    # emotion: str  (e.g. "happy")
    # prob:    float en porcentaje (e.g. 87.3)
"""
import numpy as np
import cv2
from deepface import DeepFace

from model.config import EMOTION_KEYS, CALIBRATION_MATRIX, ANALYSIS_SIZE


def analyze_emotion(frame) -> tuple[str, float]:
    """
    Analiza la emoción dominante en un frame BGR.

    Parámetros
    ----------
    frame : np.ndarray
        Frame en formato BGR (OpenCV).

    Retorna
    -------
    (emotion, probability)
        emotion     — clave de emoción en EMOTION_KEYS
        probability — confianza en porcentaje [0–100]

    Lanza
    -----
    Exception si DeepFace falla (sin rostros detectados, etc.).
    """
    af = cv2.resize(frame, ANALYSIS_SIZE)
    result = DeepFace.analyze(
        af,
        actions=["emotion"],
        enforce_detection=False,
        silent=True,
        detector_backend="mtcnn",
    )

    # Si hay varios rostros, tomar el más grande
    if isinstance(result, list) and len(result) > 1:
        res = max(
            result,
            key=lambda r: r.get("region", {}).get("w", 0) * r.get("region", {}).get("h", 0),
        )
    else:
        res = result[0] if isinstance(result, list) else result

    # Vector de probabilidades raw
    raw = res.get("emotion", {})
    vec = np.array([raw.get(k, 0.0) for k in EMOTION_KEYS], dtype=np.float32)
    s = vec.sum()
    # TODO: NORMALIZACIÓN — se fuerza suma=1 sobre el vector raw de DeepFace; revisar si ya viene normalizado
    if s > 0:
        vec /= s

    # TODO: APLICACIÓN DE MATRIZ DE CALIBRACIÓN — multiplicación vec @ CALIBRATION_MATRIX redistribuye las probabilidades
    # TODO: NORMALIZACIÓN POST-CALIBRACIÓN — se renormaliza corr para que sume 1 antes de tomar argmax
    # Aplicar matriz de calibración
    corr = vec @ CALIBRATION_MATRIX
    corr /= corr.sum()

    idx = int(np.argmax(corr))
    return EMOTION_KEYS[idx], float(corr[idx]) * 100.0
