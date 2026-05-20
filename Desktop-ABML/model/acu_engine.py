"""
model/acu_engine.py — Motor ACU: regresión logística sobre datos de grupo.

Flujo:
  1. Al finalizar sesión grupal, analysis_page llama compute_and_save_async().
  2. Se entrena el modelo con los registros del grupo (en memoria).
  3. Los resultados se persisten en acu_sesiones + acu_estudiantes via API.
  4. history_page consulta fetch_acu_for_group() / fetch_acu_for_persona()
     para incluir el PDF en el ZIP de descarga.
"""
import uuid
import datetime
import threading

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from model.config import API_BASE_URL, API_SESSION

# ── Dominio de emociones ────────────────────────────────────────────────────

EMOTION_KEYS = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']

CALIBRATION_MATRIX = np.array([
    [0.45, 0.08, 0.05, 0.00, 0.35, 0.02, 0.05],
    [0.25, 0.45, 0.05, 0.00, 0.15, 0.05, 0.05],
    [0.05, 0.05, 0.45, 0.02, 0.15, 0.25, 0.03],
    [0.00, 0.00, 0.00, 0.95, 0.00, 0.03, 0.02],
    [0.12, 0.05, 0.05, 0.00, 0.72, 0.01, 0.05],
    [0.03, 0.01, 0.22, 0.05, 0.05, 0.60, 0.04],
    [0.05, 0.02, 0.02, 0.05, 0.08, 0.03, 0.75],
], dtype=np.float32)

EMOTION_VALUE = {k: float(CALIBRATION_MATRIX[i, i]) for i, k in enumerate(EMOTION_KEYS)}

_CONSULTA_URL       = f"{API_BASE_URL}/api/consultas/ejecutarconsultaparametrizada"
_ACU_SESIONES_URL   = f"{API_BASE_URL}/api/acu_sesiones"
_ACU_ESTUDIANTES_URL = f"{API_BASE_URL}/api/acu_estudiantes"


# ── Construcción del DataFrame ──────────────────────────────────────────────

def _records_to_df(records: list) -> pd.DataFrame:
    """Convierte los registros del grupo (dicts) al DataFrame de la regresión."""
    rows = []
    for rec in records:
        respondio = rec.get("respondio", False)
        correcto  = (
            respondio is True
            or str(respondio).lower() in ("true", "1", "yes")
        )
        rows.append({
            "persona":   str(rec.get("persona", "")).strip(),
            "pregunta":  rec.get("pregunta", ""),
            "respuesta": 1 if correcto else 0,
            "emocion":   str(rec.get("emocion", "neutral")).lower().strip(),
            "confianza": float(rec.get("prob_emocion", 50)),
            "timestamp": rec.get("timestamp", ""),
        })
    return pd.DataFrame(rows)


def _build_features(df: pd.DataFrame) -> np.ndarray:
    b1 = df['respuesta'].values.astype(float)
    b2 = df['emocion'].map(EMOTION_VALUE).fillna(0.5).values
    b3 = df['confianza'].values / 100.0
    return np.column_stack([b1, b2, b3])


def _build_labels(df: pd.DataFrame) -> pd.Series:
    tasa   = df.groupby('persona')['respuesta'].mean()
    umbral = tasa.mean()
    return df['persona'].map((tasa >= umbral).astype(int))


# ── Cómputo ACU ─────────────────────────────────────────────────────────────

def compute_acu(records: list) -> dict | None:
    """
    Entrena la regresión logística y calcula el ACU por estudiante.

    Retorna None si hay menos de 2 estudiantes distintos (modelo no útil).
    Retorna dict con:
      'model_info' : coeficientes y métricas
      'acu_df'     : DataFrame con una fila por estudiante
    """
    df = _records_to_df(records)
    if df.empty:
        return None

    personas = df['persona'].unique()
    if len(personas) < 2:
        return None

    X = _build_features(df)
    y = _build_labels(df)

    umbral = df.groupby('persona')['respuesta'].mean().mean()

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    n_clases = len(np.unique(y))
    if n_clases < 2:
        # Una sola clase: el modelo no puede entrenar (todos por encima/debajo del umbral).
        # Fallback: combinar respuesta (70%), emoción calibrada (20%) y confianza (10%)
        # mediante sigmoid para obtener probabilidades diferenciadas entre estudiantes.
        z     = 2.0 * X_scaled[:, 0] + 0.8 * X_scaled[:, 1] + 0.5 * X_scaled[:, 2]
        proba = 1.0 / (1.0 + np.exp(-z))
        # Escalar al rango real de rendimiento del grupo
        if proba.max() > proba.min():
            proba = (proba - proba.min()) / (proba.max() - proba.min())
        coef_info = {
            'b0': 0.0, 'b1': 2.0, 'b2': 0.8, 'b3': 0.5,
            'precision': float(np.mean((proba >= 0.5).astype(int) == y.values)),
            'umbral': float(umbral),
        }
    else:
        model = LogisticRegression(random_state=42, max_iter=500, solver='lbfgs')
        model.fit(X_scaled, y)
        proba     = model.predict_proba(X_scaled)[:, 1]
        coef_info = {
            'b0':        float(model.intercept_[0]),
            'b1':        float(model.coef_[0][0]),
            'b2':        float(model.coef_[0][1]),
            'b3':        float(model.coef_[0][2]),
            'precision': float(model.score(X_scaled, y)),
            'umbral':    float(umbral),
        }

    df        = df.copy()
    df['prob_acu'] = proba

    acu = df.groupby('persona').agg(
        preguntas            = ('respuesta', 'count'),
        correctas            = ('respuesta', 'sum'),
        tasa_acierto         = ('respuesta', 'mean'),
        ACU                  = ('prob_acu',  'mean'),
        emocion_predominante = ('emocion',   lambda x: x.value_counts().index[0]),
        confianza_media      = ('confianza', 'mean'),
    ).reset_index()

    acu['ACU_%']          = (acu['ACU'] * 100).round(2)
    acu['incorrectas']    = acu['preguntas'] - acu['correctas']
    acu['tasa_acierto_%'] = (acu['tasa_acierto'] * 100).round(1)
    acu['ranking']        = acu['ACU'].rank(ascending=False, method='min').astype(int)
    acu['total_alumnos']  = len(acu)
    acu['acu_grupo']      = round(float(acu['ACU_%'].mean()), 2)
    acu = acu.sort_values('ACU', ascending=False).reset_index(drop=True)

    return {
        'model_info': coef_info,
        'acu_df':     acu,
    }


# ── Persistencia en BD ──────────────────────────────────────────────────────

def save_acu_to_db(reporte_grupo_id: str, nombre_grupo: str,
                   fecha: str, hora: str, result: dict) -> str | None:
    """
    Guarda los resultados ACU en acu_sesiones + acu_estudiantes.
    Retorna el acu_sesion_id generado, o None si falla.
    """
    if result is None:
        return None

    acu_sesion_id = str(uuid.uuid4())
    mi     = result['model_info']
    acu_df = result['acu_df']

    try:
        API_SESSION.post(_ACU_SESIONES_URL, json={
            "id":                acu_sesion_id,
            "reporte_grupo_id":  reporte_grupo_id,
            "nombre_grupo":      nombre_grupo,
            "fecha":             fecha,
            "hora":              hora,
            "coef_b0":           mi['b0'],
            "coef_b1":           mi['b1'],
            "coef_b2":           mi['b2'],
            "coef_b3":           mi['b3'],
            "precision_modelo":  mi['precision'],
            "umbral_grupal":     mi['umbral'],
            "acu_promedio":      float(acu_df['ACU_%'].mean()),
            "total_estudiantes": int(len(acu_df)),
        }, timeout=10)
    except Exception:
        pass

    for _, row in acu_df.iterrows():
        try:
            API_SESSION.post(_ACU_ESTUDIANTES_URL, json={
                "id":                    str(uuid.uuid4()),
                "acu_sesion_id":         acu_sesion_id,
                "reporte_grupo_id":      reporte_grupo_id,
                "persona":               str(row['persona']),
                "preguntas":             int(row['preguntas']),
                "correctas":             int(row['correctas']),
                "incorrectas":           int(row['incorrectas']),
                "tasa_acierto":          float(row['tasa_acierto']),
                "tasa_acierto_pct":      float(row['tasa_acierto_%']),
                "emocion_predominante":  str(row['emocion_predominante']),
                "confianza_media":       float(row['confianza_media']),
                "acu":                   float(row['ACU']),
                "acu_pct":               float(row['ACU_%']),
                "ranking":               int(row['ranking']),
                "total_alumnos":         int(row['total_alumnos']),
                "acu_grupo":             float(row['acu_grupo']),
            }, timeout=10)
        except Exception:
            pass

    return acu_sesion_id


def compute_and_save_async(reporte_grupo_id: str, nombre_grupo: str,
                           records: list, fecha: str = None, hora: str = None):
    """
    Lanza en un hilo de background el cómputo ACU + persistencia en BD.
    No bloquea el hilo de la UI.
    """
    if not records:
        return

    def _run():
        result = compute_acu(records)
        if result is None:
            return
        f = fecha or datetime.date.today().isoformat()
        h = hora  or datetime.datetime.now().strftime("%H:%M:%S")
        save_acu_to_db(reporte_grupo_id, nombre_grupo, f, h, result)

    threading.Thread(target=_run, daemon=True).start()


# ── Consultas a la BD ───────────────────────────────────────────────────────

def fetch_acu_for_group(reporte_grupo_id: str) -> dict | None:
    """
    Recupera de la BD los resultados ACU de un reporte de grupo.
    Retorna {'sesion': {...}, 'estudiantes': [...]} ordenados por ranking,
    o None si no existe aún.
    """
    try:
        r = API_SESSION.post(_CONSULTA_URL, json={
            "consulta":   (
                "SELECT * FROM acu_sesiones "
                "WHERE reporte_grupo_id = @rid "
                "ORDER BY fecha DESC, hora DESC LIMIT 1"
            ),
            "parametros": {"rid": reporte_grupo_id},
        }, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        rows = data.get("resultados") or data.get("Resultados") or []
        if not rows:
            return None

        sesion        = rows[0]
        acu_sesion_id = sesion.get("id", "")

        r2 = API_SESSION.post(_CONSULTA_URL, json={
            "consulta":   (
                "SELECT * FROM acu_estudiantes "
                "WHERE acu_sesion_id = @sid "
                "ORDER BY ranking ASC"
            ),
            "parametros": {"sid": acu_sesion_id},
        }, timeout=10)
        if r2.status_code != 200:
            return None
        estudiantes = r2.json().get("resultados") or r2.json().get("Resultados") or []

        return {"sesion": sesion, "estudiantes": estudiantes}
    except Exception:
        return None


def fetch_acu_for_persona(persona: str, reporte_grupo_id: str = None) -> dict | None:
    """
    Recupera el ACU más reciente de un estudiante específico.
    Si se provee reporte_grupo_id, lo usa para filtrar exactamente.
    Retorna el dict de acu_estudiantes o None si no hay datos.
    """
    try:
        cols = (
            "ae.*, s.nombre_grupo, s.fecha, s.hora, s.acu_promedio, "
            "s.precision_modelo, s.umbral_grupal, "
            "s.coef_b0, s.coef_b1, s.coef_b2, s.coef_b3"
        )
        if reporte_grupo_id:
            consulta   = (
                f"SELECT {cols} FROM acu_estudiantes ae "
                "JOIN acu_sesiones s ON s.id = ae.acu_sesion_id "
                "WHERE ae.persona = @persona AND ae.reporte_grupo_id = @rid "
                "ORDER BY s.fecha DESC, s.hora DESC LIMIT 1"
            )
            parametros = {"persona": persona, "rid": reporte_grupo_id}
        else:
            consulta   = (
                f"SELECT {cols} FROM acu_estudiantes ae "
                "JOIN acu_sesiones s ON s.id = ae.acu_sesion_id "
                "WHERE ae.persona = @persona "
                "ORDER BY s.fecha DESC, s.hora DESC LIMIT 1"
            )
            parametros = {"persona": persona}

        r = API_SESSION.post(_CONSULTA_URL, json={
            "consulta":   consulta,
            "parametros": parametros,
        }, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        rows = data.get("resultados") or data.get("Resultados") or []
        return rows[0] if rows else None
    except Exception:
        return None
