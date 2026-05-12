"""
model/session_manager.py — Persistencia de sesiones via API + directorio local para imágenes.
"""
import os
import re
import csv
import uuid
import datetime
import threading

from model.config import API_BASE_URL, DATASET_DIR, API_SESSION

_CONSULTA_URL = f"{API_BASE_URL}/api/consultas/ejecutarconsultaparametrizada"
_SESIONES_URL = f"{API_BASE_URL}/api/sesiones"
_SP_URL       = f"{API_BASE_URL}/api/sesion_preguntas"


def _local_dir(session_id: str) -> str:
    return os.path.join(DATASET_DIR, "sessions", session_id)


def load_sessions() -> list:
    try:
        r = API_SESSION.get(_SESIONES_URL, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        sessions = data.get("datos", [])
        result   = []
        for s in sessions:
            sid = s.get("id", "")
            result.append({
                "id":             sid,
                "name":           s.get("nombre_persona", ""),
                "question_group": s.get("grupo_nombre", ""),
                "date":           str(s.get("fecha", ""))[:10],
                "start_time":     s.get("hora_inicio", ""),
                "end_time":       s.get("hora_fin"),
                "dir":            _local_dir(sid),
                "questions":      [],
            })
        return result
    except Exception:
        return []


def load_group_reports() -> list:
    """Lee los CSVs de grupo guardados localmente en DATASET_DIR/grupos/."""
    grupos_dir = os.path.join(DATASET_DIR, "grupos")
    if not os.path.isdir(grupos_dir):
        return []

    reports = []
    pattern = re.compile(r'^grupo_(.+)_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})\.csv$')
    for fname in os.listdir(grupos_dir):
        m = pattern.match(fname)
        if not m:
            continue
        fpath      = os.path.join(grupos_dir, fname)
        group_name = m.group(1)
        date_str   = m.group(2)
        time_str   = m.group(3).replace("-", ":")
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                records = list(csv.DictReader(f))
        except Exception:
            continue
        # Personas en el orden en que aparecen (sin duplicados)
        seen, persons = set(), []
        for rec in records:
            p = rec.get("persona", "")
            if p and p not in seen:
                seen.add(p)
                persons.append(p)
        reports.append({
            "id":         fname,
            "filepath":   fpath,
            "group_name": group_name,
            "date":       date_str,
            "time":       time_str,
            "persons":    persons,
            "records":    records,
        })

    return sorted(reports, key=lambda x: (x["date"], x["time"]), reverse=True)


def delete_group_report(filepath: str) -> bool:
    """Elimina un archivo de reporte de grupo."""
    try:
        os.remove(filepath)
        return True
    except Exception:
        return False


def create_session(name: str, questions: list, question_group: str = None) -> dict:
    sid = str(uuid.uuid4())[:8]
    now = datetime.datetime.now()

    # Crear directorio local para imágenes (sin red — inmediato)
    local_dir = _local_dir(sid)
    os.makedirs(os.path.join(local_dir, "images"), exist_ok=True)

    session = {
        "id":             sid,
        "name":           name,
        "questions":      questions,
        "question_group": question_group,
        "date":           now.strftime("%Y-%m-%d"),
        "start_time":     now.strftime("%H:%M"),
        "end_time":       None,
        "dir":            local_dir,
    }

    # Persistir en la API en background — no bloquear el hilo de la UI
    def _persist():
        # 1) Crear sesión primero (los registros de preguntas tienen FK a esta)
        try:
            API_SESSION.post(_SESIONES_URL, json={
                "id":             sid,
                "nombre_persona": name,
                "grupo_nombre":   question_group or "",
                "fecha":          now.strftime("%Y-%m-%d"),
                "hora_inicio":    now.strftime("%H:%M"),
                "hora_fin":       None,
            }, timeout=10)
        except Exception:
            return  # Sin sesión en BD no tiene sentido guardar preguntas

        # 2) Guardar preguntas en paralelo — 1 hilo por pregunta, todos a la vez
        def _post_q(q):
            if isinstance(q, str):
                q = {"text": q, "options": [], "correct": -1}
            try:
                API_SESSION.post(_SP_URL, json={
                    "sesion_id": sid,
                    "texto":     q.get("text", ""),
                    "opciones":  q.get("options", []),
                    "correcto":  int(q.get("correct", -1)),
                }, timeout=10)
            except Exception:
                pass

        workers = [threading.Thread(target=_post_q, args=(q,), daemon=True)
                   for q in questions[:]]
        for w in workers:
            w.start()

    threading.Thread(target=_persist, daemon=True).start()
    return session


def delete_session(session_id: str) -> bool:
    """Elimina la sesión del API y su directorio local de imágenes. Retorna True si tuvo éxito."""
    try:
        r = API_SESSION.delete(f"{_SESIONES_URL}/id/{session_id}", timeout=10)
        if r.status_code not in (200, 204):
            return False
    except Exception:
        return False

    local_dir = _local_dir(session_id)
    if os.path.isdir(local_dir):
        import shutil
        try:
            shutil.rmtree(local_dir)
        except Exception:
            pass

    return True


def finish_session(session_id: str) -> None:
    hora_fin = datetime.datetime.now().strftime("%H:%M")

    def _put():
        try:
            API_SESSION.put(
                f"{_SESIONES_URL}/id/{session_id}",
                json={"hora_fin": hora_fin},
                timeout=10,
            )
        except Exception:
            pass

    threading.Thread(target=_put, daemon=True).start()
