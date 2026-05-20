"""
model/acu_pdf.py — Generador de reportes PDF ACU (grupal e individual).

Ambas funciones retornan bytes (PDF en memoria) listos para escribir en un ZIP.

  generar_pdf_grupo(sesion, estudiantes) → bytes
  generar_pdf_estudiante(estudiante, nombre_grupo, fecha_sesion) → bytes
"""
import io
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

# ── Paleta de colores ────────────────────────────────────────────────────────

AZUL_OSCURO = colors.HexColor("#003087")
AZUL_CLARO  = colors.HexColor("#e8eef7")
VERDE       = colors.HexColor("#1a7a4a")
NARANJA     = colors.HexColor("#d97706")
ROJO        = colors.HexColor("#c0392b")
GRIS_CLARO  = colors.HexColor("#f5f5f5")
GRIS_BORDE  = colors.HexColor("#cccccc")
BLANCO      = colors.white
NEGRO       = colors.HexColor("#1a1a1a")

EMOTION_ES = {
    "angry": "Enojo", "disgust": "Disgusto", "fear": "Miedo",
    "happy": "Alegria", "sad": "Tristeza", "surprise": "Sorpresa",
    "neutral": "Neutral",
}


# ── Estilos ──────────────────────────────────────────────────────────────────

def _E():
    return {
        "titulo":    ParagraphStyle("titulo",    fontName="Helvetica-Bold",  fontSize=16,
                                    textColor=BLANCO,  alignment=TA_CENTER, spaceAfter=2),
        "subtitulo": ParagraphStyle("subtitulo", fontName="Helvetica",       fontSize=10,
                                    textColor=colors.HexColor("#cce0ff"), alignment=TA_CENTER),
        "seccion":   ParagraphStyle("seccion",   fontName="Helvetica-Bold",  fontSize=11,
                                    textColor=AZUL_OSCURO, spaceBefore=14, spaceAfter=4),
        "pie":       ParagraphStyle("pie",       fontName="Helvetica",       fontSize=8,
                                    textColor=colors.HexColor("#888888"), alignment=TA_CENTER),
        "ch":        ParagraphStyle("ch",        fontName="Helvetica-Bold",  fontSize=9,
                                    textColor=AZUL_OSCURO, alignment=TA_CENTER),
        "cv":        ParagraphStyle("cv",        fontName="Helvetica-Bold",  fontSize=18,
                                    textColor=NEGRO, alignment=TA_CENTER),
        "cs":        ParagraphStyle("cs",        fontName="Helvetica",       fontSize=9,
                                    textColor=colors.HexColor("#555555"), alignment=TA_CENTER),
        "interp":    ParagraphStyle("interp",    fontName="Helvetica",       fontSize=10,
                                    textColor=NEGRO, leading=14, spaceAfter=6),
        "nombre":    ParagraphStyle("nombre",    fontName="Helvetica-Bold",  fontSize=20,
                                    textColor=NEGRO, alignment=TA_CENTER,
                                    spaceBefore=8, spaceAfter=8),
        "subnombre": ParagraphStyle("subnombre", fontName="Helvetica",       fontSize=10,
                                    textColor=colors.HexColor("#555555"),
                                    alignment=TA_CENTER, spaceAfter=12),
        "puntaje":   ParagraphStyle("puntaje",   fontName="Helvetica-Bold",  fontSize=38,
                                    textColor=BLANCO, alignment=TA_CENTER),
        "nivel_lbl": ParagraphStyle("nivel_lbl", fontName="Helvetica-Bold",  fontSize=13,
                                    textColor=BLANCO, alignment=TA_CENTER),
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _nivel(pct: float) -> str:
    if pct >= 70:   return "ALTO"
    elif pct >= 50: return "MEDIO"
    else:           return "BAJO"


def _color_nivel(nivel: str) -> colors.Color:
    return {"ALTO": VERDE, "MEDIO": NARANJA, "BAJO": ROJO}[nivel]


def _encabezado(E, titulo_txt: str, sub_txt: str, ancho: float):
    data = [
        [Paragraph(titulo_txt, E["titulo"])],
        [Paragraph(sub_txt,    E["subtitulo"])],
    ]
    t = Table(data, colWidths=[ancho])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), AZUL_OSCURO),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    return t


def _barra_escala(acu_pct: float, ancho: float):
    segmentos = 20
    w_seg     = ancho / segmentos
    pos       = max(0, min(int(acu_pct / 100 * segmentos), segmentos - 1))
    nivel     = _nivel(acu_pct)

    celdas, estilos = [], [
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("GRID",          (0, 0), (-1, -1), 0.5, GRIS_BORDE),
    ]

    for i in range(segmentos):
        bg = (colors.HexColor("#fde8e8") if i < 10
              else colors.HexColor("#fef3cd") if i < 14
              else colors.HexColor("#d4edda"))
        if i == pos:
            estilos.append(("BACKGROUND", (i, 0), (i, 0), _color_nivel(nivel)))
            estilos.append(("TEXTCOLOR",  (i, 0), (i, 0), BLANCO))
            celdas.append(Paragraph(
                "▲",
                ParagraphStyle("mk", fontName="Helvetica-Bold", fontSize=8,
                               alignment=TA_CENTER, textColor=BLANCO),
            ))
        else:
            estilos.append(("BACKGROUND", (i, 0), (i, 0), bg))
            celdas.append("")

    t = Table([celdas], colWidths=[w_seg] * segmentos, rowHeights=[16])
    t.setStyle(TableStyle(estilos))
    return t


def _texto_interpretacion(nivel: str, nombre: str, correctas: int,
                           preguntas: int, emocion_raw: str) -> str:
    primer_nombre = nombre.split()[0]
    emo_es        = EMOTION_ES.get(emocion_raw.lower(), emocion_raw)
    incorrectas   = preguntas - correctas

    if nivel == "ALTO":
        return (
            f"{primer_nombre} demuestra un <b>alto nivel de comprension</b> del tema evaluado. "
            f"Respondio correctamente {correctas} de {preguntas} preguntas "
            f"con una emocion predominante de <b>{emo_es.lower()}</b>, lo que sugiere "
            f"seguridad y confianza durante el proceso de evaluacion. "
            f"Se recomienda mantener el ritmo de estudio y profundizar en temas avanzados."
        )
    elif nivel == "MEDIO":
        return (
            f"{primer_nombre} muestra un <b>nivel medio de comprension</b>. "
            f"Respondio correctamente {correctas} de {preguntas} preguntas "
            f"e incorrectamente {incorrectas}. "
            f"La emocion predominante fue <b>{emo_es.lower()}</b>. "
            f"Se recomienda refuerzo en los temas donde hubo dificultad y "
            f"estrategias para reducir la tension emocional durante la evaluacion."
        )
    return (
        f"{primer_nombre} presenta un <b>nivel bajo de comprension</b> segun los datos recolectados. "
        f"Respondio correctamente {correctas} de {preguntas} preguntas. "
        f"La emocion predominante fue <b>{emo_es.lower()}</b>, lo que puede indicar "
        f"dificultades de concentracion o inseguridad. "
        f"Se recomienda atencion personalizada y refuerzo tematico prioritario."
    )


def _pie_pagina(E, historia: list):
    historia.append(Spacer(1, 16))
    historia.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_BORDE))
    historia.append(Spacer(1, 4))
    historia.append(Paragraph(
        f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}  ·  "
        "Sistema de Analisis ACU  ·  "
        "Modelo: Regresion Logistica [b1=respuesta, b2=emocion_norm, b3=confianza_norm]",
        E["pie"],
    ))


# ── PDF GRUPAL ───────────────────────────────────────────────────────────────

def generar_pdf_grupo(sesion: dict, estudiantes: list) -> bytes:
    """
    Un único PDF con el resumen del grupo y el ranking completo.

    Parámetros:
      sesion      — fila de acu_sesiones  (dict)
      estudiantes — filas de acu_estudiantes ordenadas por ranking (list[dict])
    """
    buf     = io.BytesIO()
    ancho   = letter[0]
    cw_body = ancho - 4 * cm

    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )
    E         = _E()
    historia  = []

    nombre_grupo = str(sesion.get("nombre_grupo", "Grupo"))
    fecha        = str(sesion.get("fecha",       ""))[:10]
    hora         = str(sesion.get("hora",        ""))[:8]
    acu_prom     = float(sesion.get("acu_promedio",     0))
    total_est    = int(  sesion.get("total_estudiantes", 0))
    precision    = float(sesion.get("precision_modelo",  0)) * 100
    umbral       = float(sesion.get("umbral_grupal",     0))
    b0           = float(sesion.get("coef_b0", 0))
    b1           = float(sesion.get("coef_b1", 0))
    b2           = float(sesion.get("coef_b2", 0))
    b3           = float(sesion.get("coef_b3", 0))

    # ── Encabezado ──────────────────────────────────────────────────────────
    historia.append(_encabezado(
        E,
        "REPORTE GRUPAL — APTITUD DE COMPRENSION Y USO (ACU)",
        f"{nombre_grupo}  ·  Sesion: {fecha}  {hora}",
        cw_body,
    ))
    historia.append(Spacer(1, 14))

    # ── Resumen numérico ────────────────────────────────────────────────────
    historia.append(Paragraph("RESUMEN DEL GRUPO", E["seccion"]))
    historia.append(HRFlowable(width="100%", thickness=0.5, color=AZUL_OSCURO))
    historia.append(Spacer(1, 6))

    mejor = estudiantes[0]  if estudiantes else {}
    peor  = estudiantes[-1] if estudiantes else {}
    cw4   = cw_body / 4

    t_res = Table([
        [Paragraph("Estudiantes",    E["ch"]),
         Paragraph("ACU Promedio",   E["ch"]),
         Paragraph("Mejor ACU",      E["ch"]),
         Paragraph("Menor ACU",      E["ch"])],
        [Paragraph(str(total_est),                               E["cv"]),
         Paragraph(f"{acu_prom:.2f}%",                          E["cv"]),
         Paragraph(f"{float(mejor.get('acu_pct', 0)):.2f}%",   E["cv"]),
         Paragraph(f"{float(peor.get('acu_pct', 0)):.2f}%",    E["cv"])],
        [Paragraph("evaluados",                                  E["cs"]),
         Paragraph(_nivel(acu_prom),                            E["cs"]),
         Paragraph(str(mejor.get("persona", "—"))[:20],         E["cs"]),
         Paragraph(str(peor.get("persona",  "—"))[:20],         E["cs"])],
    ], colWidths=[cw4]*4)

    t_res.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), AZUL_CLARO),
        ("GRID",          (0, 0), (-1, -1), 0.5, GRIS_BORDE),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    historia.append(t_res)
    historia.append(Spacer(1, 6))

    # Parámetros del modelo
    historia.append(Paragraph(
        f"Modelo: P(Z=1) = sigmoid({b0:+.4f} {b1:+.4f}·respuesta "
        f"{b2:+.4f}·emocion_norm {b3:+.4f}·confianza_norm)   "
        f"Precision: {precision:.1f}%   Umbral grupal: {umbral:.3f}",
        ParagraphStyle("modelo", fontName="Helvetica", fontSize=8,
                       textColor=colors.HexColor("#555555")),
    ))
    historia.append(Spacer(1, 12))

    # ── Tabla de ranking ────────────────────────────────────────────────────
    historia.append(Paragraph("RANKING DE ESTUDIANTES", E["seccion"]))
    historia.append(HRFlowable(width="100%", thickness=0.5, color=AZUL_OSCURO))
    historia.append(Spacer(1, 6))

    proporciones = [0.05, 0.20, 0.07, 0.07, 0.09, 0.16, 0.09, 0.10, 0.17]
    col_ws       = [cw_body * p for p in proporciones]

    th  = ParagraphStyle("th",  fontName="Helvetica-Bold", fontSize=8,
                          textColor=AZUL_OSCURO, alignment=TA_CENTER)
    td  = ParagraphStyle("td",  fontName="Helvetica",      fontSize=9,
                          textColor=NEGRO,       alignment=TA_CENTER)
    tdl = ParagraphStyle("tdl", fontName="Helvetica",      fontSize=9,
                          textColor=NEGRO,       alignment=TA_LEFT)

    filas = [[
        Paragraph("#",            th),
        Paragraph("Estudiante",   th),
        Paragraph("Preg.",        th),
        Paragraph("Corr.",        th),
        Paragraph("Acierto%",     th),
        Paragraph("Emocion Dom.", th),
        Paragraph("Conf.%",       th),
        Paragraph("ACU%",         th),
        Paragraph("Nivel",        th),
    ]]

    row_colors = []
    for est in estudiantes:
        pct_e   = float(est.get("acu_pct", 0))
        niv_e   = _nivel(pct_e)
        emo_str = EMOTION_ES.get(str(est.get("emocion_predominante", "")).lower(),
                                 str(est.get("emocion_predominante", "")))
        bg_e = (colors.HexColor("#e8f5e9") if niv_e == "ALTO"
                else colors.HexColor("#fff8e1") if niv_e == "MEDIO"
                else colors.HexColor("#ffebee"))
        row_colors.append(bg_e)

        filas.append([
            Paragraph(str(est.get("ranking", "")),                td),
            Paragraph(str(est.get("persona",  ""))[:24],          tdl),
            Paragraph(str(int(est.get("preguntas", 0))),          td),
            Paragraph(str(int(est.get("correctas", 0))),          td),
            Paragraph(f"{float(est.get('tasa_acierto_pct',0)):.1f}%", td),
            Paragraph(emo_str,                                    td),
            Paragraph(f"{float(est.get('confianza_media',0)):.1f}%",  td),
            Paragraph(f"{pct_e:.2f}%",                            td),
            Paragraph(niv_e, ParagraphStyle(
                "nv", fontName="Helvetica-Bold", fontSize=9,
                alignment=TA_CENTER, textColor=_color_nivel(niv_e),
            )),
        ])

    rank_styles = [
        ("BACKGROUND",    (0, 0), (-1, 0), AZUL_CLARO),
        ("GRID",          (0, 0), (-1, -1), 0.5, GRIS_BORDE),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]
    for idx, bg in enumerate(row_colors, start=1):
        rank_styles.append(("BACKGROUND", (0, idx), (-1, idx), bg))

    t_rank = Table(filas, colWidths=col_ws)
    t_rank.setStyle(TableStyle(rank_styles))
    historia.append(t_rank)

    _pie_pagina(E, historia)
    doc.build(historia)
    return buf.getvalue()


# ── PDF INDIVIDUAL ───────────────────────────────────────────────────────────

def generar_pdf_estudiante(estudiante: dict,
                           nombre_grupo: str = "",
                           fecha_sesion: str = "") -> bytes:
    """
    PDF individual estilo ICFES para un estudiante.

    Parámetros:
      estudiante   — fila de acu_estudiantes (dict); puede incluir campos
                     extra de acu_sesiones si se obtuvo por JOIN.
      nombre_grupo — nombre del grupo para el encabezado.
      fecha_sesion — fecha formateada para el encabezado.
    """
    buf     = io.BytesIO()
    ancho   = letter[0]
    cw_body = ancho - 4 * cm

    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )
    E        = _E()
    historia = []

    nombre      = str(estudiante.get("persona",              "Estudiante"))
    acu_pct     = float(estudiante.get("acu_pct",            0))
    nivel       = _nivel(acu_pct)
    color_niv   = _color_nivel(nivel)
    emo_raw     = str(estudiante.get("emocion_predominante", "neutral")).lower()
    emo_es      = EMOTION_ES.get(emo_raw, emo_raw)
    ranking     = int(  estudiante.get("ranking",      1))
    total_alum  = int(  estudiante.get("total_alumnos", 1))
    acu_grupo_v = float(estudiante.get("acu_grupo",    0))
    correctas   = int(  estudiante.get("correctas",    0))
    preguntas   = int(  estudiante.get("preguntas",    1))
    incorrectas = int(  estudiante.get("incorrectas",  0))
    tasa_ac     = float(estudiante.get("tasa_acierto", 0))
    conf_media  = float(estudiante.get("confianza_media", 0))

    grp  = nombre_grupo or str(estudiante.get("nombre_grupo", "Grupo"))
    fech = fecha_sesion or str(estudiante.get("fecha",        ""))[:10]

    # ── Encabezado ──────────────────────────────────────────────────────────
    historia.append(_encabezado(
        E,
        "REPORTE INDIVIDUAL DE COMPRENSION — ACU",
        f"{grp}  ·  Sesion: {fech}",
        cw_body,
    ))
    historia.append(Spacer(1, 12))

    # ── Nombre del estudiante ───────────────────────────────────────────────
    historia.append(Paragraph(nombre, E["nombre"]))
    historia.append(Paragraph(
        f"Posicion en el grupo: {ranking} de {total_alum}  |  "
        f"ACU promedio del grupo: {acu_grupo_v:.2f}%",
        E["subnombre"],
    ))
    historia.append(HRFlowable(width="100%", thickness=1, color=GRIS_BORDE))
    historia.append(Spacer(1, 10))

    # ── Bloque de puntaje ACU ───────────────────────────────────────────────
    bloque = Table(
        [[Paragraph(f"{acu_pct}%",              E["puntaje"])],
         [Paragraph(f"NIVEL {nivel} DE COMPRENSION", E["nivel_lbl"])]],
        colWidths=[cw_body],
    )
    bloque.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), color_niv),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    historia.append(bloque)
    historia.append(Spacer(1, 6))

    historia.append(_barra_escala(acu_pct, cw_body))
    historia.append(Paragraph(
        "0%  ─────────────────  50%  ─────────────────  100%",
        ParagraphStyle("esc", fontName="Helvetica", fontSize=7,
                       textColor=colors.HexColor("#888888"), alignment=TA_CENTER),
    ))
    historia.append(Spacer(1, 12))

    # ── Desempeño en preguntas ──────────────────────────────────────────────
    historia.append(Paragraph("DESEMPENO EN PREGUNTAS", E["seccion"]))
    historia.append(HRFlowable(width="100%", thickness=0.5, color=AZUL_OSCURO))
    historia.append(Spacer(1, 6))

    cw3 = cw_body / 3
    t_preg = Table([
        [Paragraph("Total",       E["ch"]),
         Paragraph("Correctas",   E["ch"]),
         Paragraph("Incorrectas", E["ch"])],
        [Paragraph(str(preguntas),   E["cv"]),
         Paragraph(str(correctas),   E["cv"]),
         Paragraph(str(incorrectas), E["cv"])],
        [Paragraph("preguntas",                      E["cs"]),
         Paragraph(f"{tasa_ac*100:.0f}% acierto",   E["cs"]),
         Paragraph(f"{(1-tasa_ac)*100:.0f}% error", E["cs"])],
    ], colWidths=[cw3, cw3, cw3])
    t_preg.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (2, 0), AZUL_CLARO),
        ("BACKGROUND",    (1, 1), (1, 2), colors.HexColor("#e8f5e9")),
        ("BACKGROUND",    (2, 1), (2, 2), colors.HexColor("#fde8e8")),
        ("GRID",          (0, 0), (-1, -1), 0.5, GRIS_BORDE),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    historia.append(t_preg)
    historia.append(Spacer(1, 12))

    # ── Análisis emocional ──────────────────────────────────────────────────
    historia.append(Paragraph("ANALISIS EMOCIONAL", E["seccion"]))
    historia.append(HRFlowable(width="100%", thickness=0.5, color=AZUL_OSCURO))
    historia.append(Spacer(1, 6))

    cw2 = cw_body / 2
    t_em = Table([
        [Paragraph("Emocion Dominante",            E["ch"]),
         Paragraph("Confianza Media del Modelo",   E["ch"])],
        [Paragraph(emo_es,                          E["cv"]),
         Paragraph(f"{conf_media:.1f}%",           E["cv"])],
        [Paragraph("detectada con mayor frecuencia",        E["cs"]),
         Paragraph("promedio de confianza por observacion", E["cs"])],
    ], colWidths=[cw2, cw2])
    t_em.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), AZUL_CLARO),
        ("GRID",          (0, 0), (-1, -1), 0.5, GRIS_BORDE),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    historia.append(t_em)
    historia.append(Spacer(1, 12))

    # ── Interpretación pedagógica ───────────────────────────────────────────
    historia.append(Paragraph("INTERPRETACION PEDAGOGICA", E["seccion"]))
    historia.append(HRFlowable(width="100%", thickness=0.5, color=AZUL_OSCURO))
    historia.append(Spacer(1, 6))

    texto      = _texto_interpretacion(nivel, nombre, correctas, preguntas, emo_raw)
    bloque_int = Table([[Paragraph(texto, E["interp"])]], colWidths=[cw_body])
    bloque_int.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GRIS_CLARO),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("BOX",           (0, 0), (-1, -1), 1, color_niv),
    ]))
    historia.append(bloque_int)

    _pie_pagina(E, historia)
    doc.build(historia)
    return buf.getvalue()
