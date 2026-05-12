"""
model/groups_manager.py — Gestión de grupos de preguntas y personas via API.

Grupos de preguntas → PostgreSQL (Railway) via API REST
Grupos de personas  → PostgreSQL (Railway) via API REST
"""
import os
import re
import json

from model.config import API_BASE_URL, API_SESSION

_CONSULTA_URL = f"{API_BASE_URL}/api/consultas/ejecutarconsultaparametrizada"
_ENTIDAD_URL  = lambda tabla: f"{API_BASE_URL}/api/{tabla}"


def _safe_filename(name: str) -> str:
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_') or "grupo"


def _q_text(q) -> str:
    return q["text"] if isinstance(q, dict) else q


def _parse_opciones(raw) -> list:
    """Convierte opciones desde string JSON o lista a list[str]."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, ValueError):
            return []
    return []


def _consulta(sql: str, params: dict = None) -> list:
    body = {"consulta": sql, "parametros": params or {}}
    r = API_SESSION.post(_CONSULTA_URL, json=body, timeout=10)
    if r.status_code == 200:
        data = r.json()
        return data.get("resultados") or data.get("Resultados") or []
    return []


# ── Grupos de Preguntas ───────────────────────────────────────────────────────

def save_question_group(name: str, questions: list) -> int:
    """Crea o reemplaza un grupo de preguntas en la BD. Retorna el id del grupo."""
    # Eliminar grupo existente con el mismo nombre
    existentes = _consulta(
        "SELECT id FROM grupos_preguntas WHERE nombre = @nombre",
        {"nombre": name}
    )
    for row in existentes:
        gid = row.get("id")
        API_SESSION.delete(f"{API_BASE_URL}/api/grupos_preguntas/id/{gid}", timeout=10)

    # Crear grupo
    fname = _safe_filename(name) + ".json"
    API_SESSION.post(_ENTIDAD_URL("grupos_preguntas"), json={
        "nombre":   name,
        "archivo":  fname,
    }, timeout=10)

    # Obtener id del grupo recién creado
    rows = _consulta(
        "SELECT id FROM grupos_preguntas WHERE nombre = @nombre ORDER BY creado_en DESC LIMIT 1",
        {"nombre": name}
    )
    if not rows:
        return -1
    grupo_id = rows[0]["id"]

    # Crear preguntas
    for idx, q in enumerate(questions):
        if isinstance(q, str):
            q = {"text": q.strip(), "options": [], "correct": -1}
        text = q.get("text", "").strip()
        if not text:
            continue
        opts    = [str(o).strip() for o in q.get("options", []) if str(o).strip()]
        correct = int(q.get("correct", -1))
        API_SESSION.post(_ENTIDAD_URL("preguntas"), json={
            "grupo_id":           grupo_id,
            "texto":              text,
            "opciones":           opts,
            "respuesta_correcta": correct,
            "orden":              idx,
        }, timeout=10)

    return grupo_id


def load_question_group(group_id: int) -> dict:
    """Carga un grupo por id desde la BD."""
    rows = _consulta(
        "SELECT id, nombre FROM grupos_preguntas WHERE id = @id",
        {"id": group_id}
    )
    if not rows:
        return {}
    nombre = rows[0]["nombre"]

    _sql = (
        "SELECT texto, opciones, respuesta_correcta "
        "FROM preguntas WHERE grupo_id = @gid ORDER BY orden"
    )
    preguntas = _consulta(_sql, {"gid": group_id})
    questions = [
        {
            "text":    p["texto"],
            "options": _parse_opciones(p.get("opciones")),
            "correct": p.get("respuesta_correcta", -1),
        }
        for p in preguntas
    ]
    return {"name": nombre, "questions": questions, "id": group_id}


def list_question_groups() -> list:
    """Retorna todos los grupos con sus preguntas."""
    grupos = _consulta("SELECT id, nombre FROM grupos_preguntas ORDER BY nombre")
    result = []
    for g in grupos:
        gid    = g["id"]
        nombre = g["nombre"]
        _sql = (
            "SELECT texto, opciones, respuesta_correcta "
            "FROM preguntas WHERE grupo_id = @gid ORDER BY orden"
        )
        preg      = _consulta(_sql, {"gid": gid})
        questions = [
            {
                "text":    p["texto"],
                "options": _parse_opciones(p.get("opciones")),
                "correct": p.get("respuesta_correcta", -1),
            }
            for p in preg
        ]
        result.append({"name": nombre, "questions": questions, "id": gid})
    return result


def delete_question_group(group_id: int) -> None:
    """Elimina un grupo (y sus preguntas en cascada) por id."""
    API_SESSION.delete(f"{API_BASE_URL}/api/grupos_preguntas/id/{group_id}", timeout=10)


def get_available_questions(person_name: str, group_name: str, all_questions: list) -> list:
    """Retorna preguntas del grupo no usadas por esta persona en sesiones previas."""
    rows = _consulta(
        """
        SELECT DISTINCT sp.texto
        FROM sesion_preguntas sp
        JOIN sesiones s ON sp.sesion_id = s.id
        WHERE s.nombre_persona = @nombre AND s.grupo_nombre = @grupo
        """,
        {"nombre": person_name, "grupo": group_name}
    )
    used = {r["texto"] for r in rows}
    return [q for q in all_questions if _q_text(q) not in used]


# ── Grupos de Personas ───────────────────────────────────────────────────────

def save_person_group(name: str, people: list) -> int:
    """Crea o reemplaza un grupo de personas en la BD. Retorna el id del grupo."""
    existentes = _consulta(
        "SELECT id FROM grupos_personas WHERE nombre = @nombre",
        {"nombre": name}
    )
    for row in existentes:
        API_SESSION.delete(f"{API_BASE_URL}/api/grupos_personas/id/{row['id']}", timeout=10)

    API_SESSION.post(_ENTIDAD_URL("grupos_personas"), json={"nombre": name}, timeout=10)

    rows = _consulta(
        "SELECT id FROM grupos_personas WHERE nombre = @nombre ORDER BY creado_en DESC LIMIT 1",
        {"nombre": name}
    )
    if not rows:
        return -1
    grupo_id = rows[0]["id"]

    for idx, p in enumerate(people):
        p = p.strip()
        if not p:
            continue
        API_SESSION.post(_ENTIDAD_URL("personas"), json={
            "grupo_id": grupo_id,
            "nombre":   p,
            "orden":    idx,
        }, timeout=10)

    return grupo_id


def load_person_group(group_id: int) -> dict:
    """Carga un grupo de personas por id desde la BD."""
    rows = _consulta(
        "SELECT id, nombre FROM grupos_personas WHERE id = @id",
        {"id": group_id}
    )
    if not rows:
        return {}
    nombre = rows[0]["nombre"]
    pers = _consulta(
        "SELECT nombre FROM personas WHERE grupo_id = @gid ORDER BY orden",
        {"gid": group_id}
    )
    return {"name": nombre, "people": [p["nombre"] for p in pers], "id": group_id}


def list_person_groups() -> list:
    """Retorna todos los grupos de personas con sus integrantes."""
    grupos = _consulta("SELECT id, nombre FROM grupos_personas ORDER BY nombre")
    result = []
    for g in grupos:
        gid  = g["id"]
        pers = _consulta(
            "SELECT nombre FROM personas WHERE grupo_id = @gid ORDER BY orden",
            {"gid": gid}
        )
        result.append({"name": g["nombre"], "people": [p["nombre"] for p in pers], "id": gid})
    return result


def delete_person_group(group_id: int) -> None:
    """Elimina un grupo de personas (y sus integrantes en cascada) por id."""
    API_SESSION.delete(f"{API_BASE_URL}/api/grupos_personas/id/{group_id}", timeout=10)


def import_person_group_from_txt(src_path: str) -> dict:
    name   = os.path.splitext(os.path.basename(src_path))[0].replace("_", " ")
    people = []
    with open(src_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("# Grupo:"):
                name = line[len("# Grupo:"):].strip()
            elif not line.startswith("#"):
                people.append(line)
    gid = save_person_group(name, people)
    return {"name": name, "people": people, "id": gid}


def import_question_group_from_txt(src_path: str) -> dict:
    """
    Importa un TXT como grupo de preguntas con opciones múltiples.

    Formato esperado:
        Nombre del grupo          ← primera línea no vacía

        1 Texto de la pregunta
        a.Opción A (C)            ← (C) marca la correcta (con o sin espacio)
        b.Opción B

        2 Texto de otra pregunta
        a.Opción A
        b.Opción B(C)
    """
    _q_re   = re.compile(r'^\s*\d+[\.\s]\s*(.+)')
    _opt_re = re.compile(r'^\s*[a-zA-Z][\.\)]\s*(.+)', re.IGNORECASE)
    _cor_re = re.compile(r'\s*\(C\)\s*', re.IGNORECASE)

    name = os.path.splitext(os.path.basename(src_path))[0].replace("_", " ")
    questions: list[dict] = []
    name_found  = False
    current_q: dict | None = None

    with open(src_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue

            # Primera línea no vacía → nombre del grupo
            if not name_found:
                name = line
                name_found = True
                continue

            # ¿Es una pregunta?  "1 texto" o "1. texto"
            q_m = _q_re.match(line)
            if q_m:
                if current_q:
                    questions.append(current_q)
                current_q = {"text": q_m.group(1).strip(), "options": [], "correct": -1}
                continue

            # ¿Es una opción?  "a.texto" o "a) texto"
            opt_m = _opt_re.match(line)
            if opt_m and current_q is not None:
                opt_text   = opt_m.group(1).strip()
                is_correct = bool(_cor_re.search(opt_text))
                opt_text   = _cor_re.sub("", opt_text).strip()
                if is_correct:
                    current_q["correct"] = len(current_q["options"])
                current_q["options"].append(opt_text)

    if current_q:
        questions.append(current_q)

    # ── Validación de formato ─────────────────────────────────────────────────
    if not questions:
        raise ValueError(
            "No se detectaron preguntas.\n"
            "Verifica que cada pregunta empiece con un número (ej: '1 texto...')."
        )

    invalid = [
        i + 1
        for i, q in enumerate(questions)
        if len(q["options"]) < 2
    ]
    if invalid:
        nums = ", ".join(str(n) for n in invalid)
        raise ValueError(
            f"La(s) pregunta(s) {nums} tiene(n) menos de 2 opciones.\n"
            "Cada pregunta debe tener mínimo 2 opciones (a. / b. ...)."
        )

    if len(questions) < 2:
        raise ValueError(
            f"El archivo solo contiene {len(questions)} pregunta.\n"
            "Se necesitan al menos 2 preguntas para crear un grupo."
        )

    gid = save_question_group(name, questions)
    return {"name": name, "questions": questions, "id": gid}
