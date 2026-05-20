"""
model/session_manager.py — Persistencia de sesiones via API + directorio local para imágenes.
"""
import os
import uuid
import json as _json
import datetime
import threading

from model.config import API_BASE_URL, DATASET_DIR, API_SESSION

_CONSULTA_URL       = f"{API_BASE_URL}/api/consultas/ejecutarconsultaparametrizada"
_SESIONES_URL       = f"{API_BASE_URL}/api/sesiones"
_SP_URL             = f"{API_BASE_URL}/api/sesion_preguntas"
_REPORTES_GRUPO_URL = f"{API_BASE_URL}/api/reportes_grupo"


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
    """
    Carga solo los metadatos de los reportes de grupo (sin 'registros').
    Los registros son potencialmente grandes; se obtienen bajo demanda con fetch_group_records().
    """
    try:
        r = API_SESSION.post(
            _CONSULTA_URL,
            json={
                "consulta":   "SELECT id, nombre_grupo, fecha, hora, personas "
                              "FROM reportes_grupo ORDER BY fecha DESC, hora DESC",
                "parametros": {},
            },
            timeout=10,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        rows = data.get("resultados") or data.get("Resultados") or []

        reports = []
        for row in rows:
            try:
                persons = _json.loads(row.get("personas") or "[]")
            except Exception:
                persons = []

            reports.append({
                "id":         str(row.get("id", "")),
                "group_name": row.get("nombre_grupo", ""),
                "date":       str(row.get("fecha", ""))[:10],
                "time":       str(row.get("hora", "")),
                "persons":    persons,
                "records":    [],   # se cargan bajo demanda
            })
        return reports
    except Exception:
        return []


def fetch_group_records(report_id: str) -> list:
    """Descarga los registros detallados de un reporte de grupo específico."""
    try:
        r = API_SESSION.post(
            _CONSULTA_URL,
            json={
                "consulta":   "SELECT registros FROM reportes_grupo WHERE id = @rid LIMIT 1",
                "parametros": {"rid": report_id},
            },
            timeout=15,
        )
        if r.status_code != 200:
            return []
        data  = r.json()
        rows  = data.get("resultados") or data.get("Resultados") or []
        if not rows:
            return []
        return _json.loads(rows[0].get("registros") or "[]")
    except Exception:
        return []


def delete_group_report(report_id: str) -> bool:
    """Elimina un reporte de grupo de la API/base de datos."""
    try:
        r = API_SESSION.delete(
            f"{_REPORTES_GRUPO_URL}/id/{report_id}",
            timeout=10,
        )
        return r.status_code in (200, 204)
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
