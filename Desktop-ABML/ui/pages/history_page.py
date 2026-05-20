"""
ui/pages/history_page.py — Pantalla 4: Historial de sesiones.
"""
import os
import csv
import zipfile
import io
import threading
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import customtkinter as ctk
from PIL import Image

import ui.theme as T
from ui.assets import FLECHA_IZQ_FILE, USUARIO_FILE, REPORTE_FILE, DESCARGA_FILE, ELIMINAR_FILE
from ui.tooltip import Tooltip
from model.session_manager import (
    load_sessions, delete_session,
    load_group_reports, delete_group_report, fetch_group_records,
)
from model.config import API_BASE_URL, API_SESSION


def _load_icon(path, hex_color, size=22):
    """Carga un PNG a 2× resolución y lo coloriza; CTkImage lo muestra nítido."""
    if not os.path.exists(path):
        return None
    hi = size * 2
    pil = Image.open(path).convert("RGBA").resize((hi, hi), Image.LANCZOS)
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    pixels = pil.load()
    for y in range(pil.height):
        for x in range(pil.width):
            _, _, _, a = pixels[x, y]
            if a > 0:
                pixels[x, y] = (r, g, b, a)
    return ctk.CTkImage(light_image=pil, dark_image=pil, size=(size, size))


class HistoryPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=T.BG_MAIN, corner_radius=0)
        self._app = app
        self._load_icons()
        self._build()

    def _load_icons(self):
        self._ico_back    = _load_icon(FLECHA_IZQ_FILE, T.TEXT_MID,     size=20)
        self._ico_usuario = _load_icon(USUARIO_FILE,    T.GREEN_PRIMARY, size=24)
        self._ico_grupo   = _load_icon(USUARIO_FILE,    "#4fc3f7",       size=24)
        self._ico_excel   = _load_icon(REPORTE_FILE,    T.GREEN_PRIMARY, size=24)
        self._ico_zip     = _load_icon(DESCARGA_FILE,   T.TEXT_LIGHT,    size=24)
        self._ico_delete  = _load_icon(ELIMINAR_FILE,   T.RED_PRIMARY,   size=22)

    # ── Construcción ─────────────────────────────────────────────────────────

    def _build(self):
        # Header — renderiza inmediatamente sin esperar datos de red
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 8))

        back_btn = ctk.CTkButton(
            header,
            text="", image=self._ico_back,
            width=42, height=42,
            fg_color=T.BG_CARD, hover_color=T.BG_HOVER,
            corner_radius=T.CORNER_RADIUS_BTN,
            anchor="center",
            command=self._app.show_main_menu,
        )
        back_btn.pack(side="left")
        Tooltip(back_btn, "Volver al menú principal")

        title_f = ctk.CTkFrame(self, fg_color="transparent")
        title_f.pack(pady=(0, 10))
        ctk.CTkLabel(title_f, text="HISTORIAL",   text_color=T.GREEN_PRIMARY, font=T.bold(24)).pack(side="left")
        ctk.CTkLabel(title_f, text=" / ANÁLISIS", text_color=T.WHITE,         font=T.bold(24)).pack(side="left")

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=40, pady=(0, 6))

        # Indicador de carga visible mientras se consulta la API
        self._loading_lbl = ctk.CTkLabel(
            self._scroll,
            text="⏳  Cargando historial...",
            text_color=T.TEXT_MID, font=T.font(14),
        )
        self._loading_lbl.pack(pady=40)

        # Footer — se actualiza cuando llegan los datos
        self._footer_lbl = ctk.CTkLabel(
            self,
            text="Cargando...",
            text_color=T.GREEN_PRIMARY, font=T.font(12),
        )
        self._footer_lbl.pack(pady=(0, 14))

        # Cargar sesiones y reportes en background para no bloquear la UI
        def _load():
            sessions      = load_sessions()
            group_reports = load_group_reports()
            self.after(0, lambda: self._populate(sessions, group_reports))

        threading.Thread(target=_load, daemon=True).start()

    def _populate(self, sessions: list, group_reports: list):
        """Puebla el scroll con los datos ya cargados. Corre en el hilo principal."""
        try:
            self._loading_lbl.destroy()
        except Exception:
            pass

        # ── Sección grupos ────────────────────────────────────────────────────
        if group_reports:
            self._section_label(self._scroll, "Grupos evaluados")
            for i, gr in enumerate(group_reports):
                self._group_card(self._scroll, i + 1, gr)

        # ── Sección individuales ──────────────────────────────────────────────
        if sessions:
            self._section_label(self._scroll, "Análisis individuales")
            for i, s in enumerate(sessions):
                self._session_card(self._scroll, i + 1, s)

        if not sessions and not group_reports:
            ctk.CTkLabel(self._scroll, text="No hay análisis registrados aún.",
                         text_color=T.TEXT_DARKER, font=T.font(14)).pack(pady=40)

        self._footer_lbl.configure(
            text=f"Grupos: {len(group_reports)}   ·   Sesiones individuales: {len(sessions)}"
        )

    def _section_label(self, parent, text: str):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(12, 4))
        ctk.CTkLabel(row, text=text, text_color=T.TEXT_MID,
                     font=T.bold(12)).pack(side="left")
        sep = ctk.CTkFrame(row, fg_color=T.BG_HOVER, height=1)
        sep.pack(side="left", fill="x", expand=True, padx=(8, 0), pady=(2, 0))

    # ── Tarjeta de grupo ──────────────────────────────────────────────────────

    def _group_card(self, parent, num: int, report: dict):
        card = ctk.CTkFrame(parent, fg_color="#0d1f2d", corner_radius=T.CORNER_RADIUS_CARD)
        card.pack(fill="x", pady=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=12, pady=10)

        # Badge número
        badge = ctk.CTkFrame(inner, fg_color="#0a2a3a", corner_radius=10, width=34, height=34)
        badge.pack_propagate(False)
        badge.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(badge, text=str(num), text_color="#4fc3f7", font=T.bold(13)).pack(expand=True)

        # Ícono grupo (azul para diferenciar de individuales)
        icon_box = ctk.CTkFrame(inner, fg_color="#0a2a3a", corner_radius=22, width=44, height=44)
        icon_box.pack_propagate(False)
        icon_box.pack(side="left", padx=(0, 12))
        if self._ico_grupo:
            ctk.CTkLabel(icon_box, image=self._ico_grupo, text="").pack(expand=True)

        # Info del grupo
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(info,
                     text=report.get("group_name", "Grupo"),
                     text_color=T.WHITE, font=T.bold(14), anchor="w").pack(anchor="w")

        persons_txt = "  ·  ".join(report.get("persons", []))
        ctk.CTkLabel(info,
                     text=f"👥 {persons_txt}",
                     text_color="#4fc3f7", font=T.font(11),
                     wraplength=380, justify="left", anchor="w").pack(anchor="w")

        detail = ctk.CTkFrame(info, fg_color="transparent")
        detail.pack(anchor="w")
        ctk.CTkLabel(detail, text=f"🗓 {report.get('date', '')}",
                     text_color=T.TEXT_DIM, font=T.font(11)).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(detail, text=f"🕐 {report.get('time', '')}",
                     text_color=T.TEXT_DIM, font=T.font(11)).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(detail, text=f"👥 {len(report.get('persons', []))} personas",
                     text_color=T.TEXT_DIM, font=T.font(11)).pack(side="left")

        # Botones
        btns_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btns_frame.pack(side="right")

        btn_excel = ctk.CTkButton(
            btns_frame,
            text="", image=self._ico_excel,
            width=46, height=46,
            fg_color=T.BG_GREEN_DARK, hover_color=T.BG_GREEN_HOVER,
            corner_radius=T.CORNER_RADIUS_BTN,
            anchor="center",
            command=lambda r=report: self._download_group_pdf(r),
        )
        btn_excel.pack(side="left", padx=(0, 6))
        Tooltip(btn_excel, "Descargar reporte PDF del ACU grupal")

        btn_zip = ctk.CTkButton(
            btns_frame,
            text="", image=self._ico_zip,
            width=46, height=46,
            fg_color=T.BG_BUTTON, hover_color=T.BG_HOVER,
            corner_radius=T.CORNER_RADIUS_BTN,
            anchor="center",
            command=lambda r=report: self._download_group(r),
        )
        btn_zip.pack(side="left", padx=(0, 6))
        Tooltip(btn_zip, "Descargar CSV del grupo (.zip)")

        btn_del = ctk.CTkButton(
            btns_frame,
            text="", image=self._ico_delete,
            width=46, height=46,
            fg_color=T.BG_RED_EXIT, hover_color="#3d1010",
            corner_radius=T.CORNER_RADIUS_BTN,
            anchor="center",
            command=lambda r=report: self._confirm_delete_group(r),
        )
        btn_del.pack(side="left")
        Tooltip(btn_del, "Eliminar reporte de grupo")

    # ── Tarjeta individual ────────────────────────────────────────────────────

    def _session_card(self, parent, num: int, session: dict):
        card = ctk.CTkFrame(parent, fg_color=T.BG_DARK, corner_radius=T.CORNER_RADIUS_CARD, height=T.HEIGHT_CARD)
        card.pack_propagate(False)
        card.pack(fill="x", pady=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=12, pady=10)

        badge = ctk.CTkFrame(inner, fg_color=T.BG_ICON_GREEN, corner_radius=10, width=34, height=34)
        badge.pack_propagate(False)
        badge.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(badge, text=str(num), text_color=T.GREEN_PRIMARY, font=T.bold(13)).pack(expand=True)

        icon_box = ctk.CTkFrame(inner, fg_color=T.BG_GREEN_DIM, corner_radius=22, width=44, height=44)
        icon_box.pack_propagate(False)
        icon_box.pack(side="left", padx=(0, 12))
        if self._ico_usuario:
            ctk.CTkLabel(icon_box, image=self._ico_usuario, text="").pack(expand=True)

        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(info, text=session.get("name", "—"),
                     text_color=T.WHITE, font=T.bold(14), anchor="w").pack(anchor="w")

        detail = ctk.CTkFrame(info, fg_color="transparent")
        detail.pack(anchor="w")
        ctk.CTkLabel(detail, text=f"🗓 {session.get('date', '')}",
                     text_color=T.TEXT_DIM, font=T.font(11)).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(detail, text=f"🕐 Inicio: {session.get('start_time', '—')}",
                     text_color=T.TEXT_DIM, font=T.font(11)).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(detail, text=f"🕑 Fin: {session.get('end_time', '—')}",
                     text_color=T.TEXT_DIM, font=T.font(11)).pack(side="left")

        btns_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btns_frame.pack(side="right")

        btn_excel = ctk.CTkButton(
            btns_frame,
            text="", image=self._ico_excel,
            width=46, height=46,
            fg_color=T.BG_GREEN_DARK, hover_color=T.BG_GREEN_HOVER,
            corner_radius=T.CORNER_RADIUS_BTN,
            anchor="center",
            command=lambda s=session: self._download_individual_pdf(s),
        )
        btn_excel.pack(side="left", padx=(0, 6))
        Tooltip(btn_excel, "Descargar reporte PDF del ACU")

        btn_zip = ctk.CTkButton(
            btns_frame,
            text="", image=self._ico_zip,
            width=46, height=46,
            fg_color=T.BG_BUTTON, hover_color=T.BG_HOVER,
            corner_radius=T.CORNER_RADIUS_BTN,
            anchor="center",
            command=lambda s=session: self._download(s),
        )
        btn_zip.pack(side="left", padx=(0, 6))
        Tooltip(btn_zip, "Descargar sesión completa (.zip)")

        btn_del = ctk.CTkButton(
            btns_frame,
            text="", image=self._ico_delete,
            width=46, height=46,
            fg_color=T.BG_RED_EXIT, hover_color="#3d1010",
            corner_radius=T.CORNER_RADIUS_BTN,
            anchor="center",
            command=lambda s=session: self._confirm_delete(s),
        )
        btn_del.pack(side="left")
        Tooltip(btn_del, "Eliminar análisis")

    # ── Eliminación ───────────────────────────────────────────────────────────

    def _confirm_delete(self, session: dict):
        name = session.get("name", "—")
        date = session.get("date", "")
        ok = mb.askyesno(
            "Eliminar análisis",
            f"¿Eliminar el análisis de {name} ({date})?\n\nEsta acción no se puede deshacer.",
            icon="warning",
        )
        if not ok:
            return
        if delete_session(session.get("id", "")):
            self._app.show_history()
        else:
            mb.showerror("Error", "No se pudo eliminar el análisis.\nVerifica la conexión con el servidor.")

    def _confirm_delete_group(self, report: dict):
        group = report.get("group_name", "—")
        date  = report.get("date", "")
        ok = mb.askyesno(
            "Eliminar reporte de grupo",
            f"¿Eliminar el reporte del grupo '{group}' ({date})?\n\nEsta acción no se puede deshacer.",
            icon="warning",
        )
        if not ok:
            return
        if delete_group_report(report.get("id", "")):
            self._app.show_history()
        else:
            mb.showerror("Error", "No se pudo eliminar el reporte.")

    # ── Helpers API ───────────────────────────────────────────────────────────

    def _fetch_registros(self, session_id: str) -> list:
        try:
            r = API_SESSION.post(
                f"{API_BASE_URL}/api/consultas/ejecutarconsultaparametrizada",
                json={
                    "consulta":   "SELECT * FROM registros WHERE sesion_id = @sid ORDER BY timestamp",
                    "parametros": {"sid": session_id},
                },
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                return data.get("resultados") or data.get("Resultados") or []
        except Exception:
            pass
        return []

    # ── Exportación Excel individual ──────────────────────────────────────────

    # ── Descarga PDF individual ACU ───────────────────────────────────────────

    def _download_individual_pdf(self, session: dict):
        persona      = session.get("name", "sesion")
        name_safe    = persona.replace(" ", "_")
        default_name = f"reporte_ACU_{name_safe}_{session.get('date', '')}.pdf"

        save_path = fd.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=default_name,
            title="Guardar reporte PDF del ACU individual",
        )
        if not save_path:
            return

        try:
            from model.acu_engine import fetch_acu_for_persona
            from model.acu_pdf   import generar_pdf_estudiante

            est_data = fetch_acu_for_persona(persona)
            if not est_data:
                mb.showerror("Sin datos ACU",
                             f"No hay reporte ACU disponible para {persona}.\n"
                             "El ACU solo se calcula en sesiones grupales.")
                return

            pdf_bytes = generar_pdf_estudiante(
                est_data,
                nombre_grupo = str(est_data.get("nombre_grupo", "")),
                fecha_sesion = str(est_data.get("fecha", ""))[:10],
            )
            with open(save_path, "wb") as f:
                f.write(pdf_bytes)

            mb.showinfo("PDF generado", f"Reporte PDF guardado en:\n{save_path}")
        except Exception as exc:
            mb.showerror("Error", f"No se pudo generar el PDF:\n{exc}")

    # ── Exportación Excel individual ──────────────────────────────────────────

    def _export_excel(self, session: dict):
        rows = self._fetch_registros(session.get("id", ""))
        if not rows:
            mb.showerror("Error", "No se encontraron datos para esta sesión.")
            return

        name_safe    = session.get("name", "sesion").replace(" ", "_")
        default_name = f"reporte_{name_safe}_{session.get('date', '')}.xlsx"

        save_path = fd.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=default_name,
            title="Guardar reporte Excel",
        )
        if not save_path:
            return

        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Resultados"

            headers  = ["Pregunta", "Respuesta (1/0)", "Respuesta correcta", "Emoción", "Confianza (%)", "Timestamp"]
            hdr_fill = PatternFill("solid", fgColor="1a3a1a")
            hdr_font = Font(bold=True, color="FFFFFF")
            thin     = Side(style="thin", color="CCCCCC")
            border   = Border(left=thin, right=thin, top=thin, bottom=thin)

            for col, h in enumerate(headers, 1):
                cell           = ws.cell(row=1, column=col, value=h)
                cell.font      = hdr_font
                cell.fill      = hdr_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border    = border
            ws.row_dimensions[1].height = 20

            for r_idx, row in enumerate(rows, 2):
                respondio      = row.get("respondio", False)
                correct_answer = row.get("respuesta_correcta", "") if respondio else ""
                conf = 0
                try:
                    conf = round(float(row.get("prob_emocion", 0)), 2)
                except (ValueError, TypeError):
                    pass

                valores    = [row.get("pregunta", ""), 1 if respondio else 0,
                              correct_answer, row.get("emocion", ""), conf,
                              str(row.get("timestamp", ""))]
                fill_color = "D6EAD6" if respondio else "FAD7D7"
                row_fill   = PatternFill("solid", fgColor=fill_color)

                for col, val in enumerate(valores, 1):
                    cell           = ws.cell(row=r_idx, column=col, value=val)
                    cell.fill      = row_fill
                    cell.border    = border
                    cell.alignment = Alignment(vertical="center",
                                               horizontal="center" if col in (2, 4, 5, 6) else "left")
                    cell.font      = Font(color="000000")

            col_widths = [46, 16, 38, 14, 14, 26]
            for col, width in enumerate(col_widths, 1):
                ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = width

            ws.freeze_panes = "A2"
            wb.save(save_path)
            mb.showinfo("Exportación completa", f"Excel guardado en:\n{save_path}")
        except ImportError:
            mb.showerror(
                "Módulo faltante",
                "Se requiere 'openpyxl' para exportar Excel.\n"
                "Instálalo con: pip install openpyxl",
            )
        except Exception as exc:
            mb.showerror("Error", f"No se pudo crear el Excel:\n{exc}")

    # ── Descarga ZIP de grupo ─────────────────────────────────────────────────

    def _download_group(self, report: dict):
        group_safe   = report.get("group_name", "grupo").replace(" ", "_")
        default_name = f"grupo_{group_safe}_{report.get('date', '')}.zip"

        save_path = fd.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP file", "*.zip")],
            initialfile=default_name,
            title="Guardar reporte de grupo como ZIP",
        )
        if not save_path:
            return

        try:
            # Cargar registros bajo demanda (no se traen al abrir el historial)
            records = fetch_group_records(report.get("id", ""))
            if not records:
                mb.showerror("Error", "No se encontraron registros para este reporte de grupo.")
                return

            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(["persona", "pregunta", "respuesta_correcta",
                              "emocion", "prob_emocion", "respondio", "timestamp"])
            for rec in records:
                respondio = rec.get("respondio", "")
                is_true   = str(respondio).lower() in ("true", "1", "yes")
                writer.writerow([
                    rec.get("persona", ""),
                    rec.get("pregunta", ""),
                    rec.get("respuesta_correcta", ""),
                    rec.get("emocion", ""),
                    rec.get("prob_emocion", ""),
                    1 if is_true else 0,
                    rec.get("timestamp", ""),
                ])

            pdf_incluido = False
            pdf_error    = ""
            with zipfile.ZipFile(save_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("registros_grupo.csv", csv_buffer.getvalue())

                # Calcular ACU directo desde los registros ya descargados — sin depender
                # de IDs en la BD. Los registros están en memoria, así que siempre funciona.
                try:
                    from model.acu_engine import compute_acu
                    from model.acu_pdf   import generar_pdf_grupo

                    result = compute_acu(records)
                    if result:
                        mi  = result["model_info"]
                        adf = result["acu_df"]

                        sesion_dict = {
                            "nombre_grupo":      report.get("group_name", "Grupo"),
                            "fecha":             report.get("date",       ""),
                            "hora":              report.get("time",       ""),
                            "acu_promedio":      float(adf["ACU_%"].mean()),
                            "total_estudiantes": int(len(adf)),
                            "coef_b0":           mi["b0"],
                            "coef_b1":           mi["b1"],
                            "coef_b2":           mi["b2"],
                            "coef_b3":           mi["b3"],
                            "precision_modelo":  mi["precision"],
                            "umbral_grupal":     mi["umbral"],
                        }

                        est_list = []
                        for _, row in adf.iterrows():
                            est_list.append({
                                "persona":              str(row["persona"]),
                                "preguntas":            int(row["preguntas"]),
                                "correctas":            int(row["correctas"]),
                                "incorrectas":          int(row["incorrectas"]),
                                "tasa_acierto":         float(row["tasa_acierto"]),
                                "tasa_acierto_pct":     float(row["tasa_acierto_%"]),
                                "emocion_predominante": str(row["emocion_predominante"]),
                                "confianza_media":      float(row["confianza_media"]),
                                "acu":                  float(row["ACU"]),
                                "acu_pct":              float(row["ACU_%"]),
                                "ranking":              int(row["ranking"]),
                                "total_alumnos":        int(row["total_alumnos"]),
                                "acu_grupo":            float(row["acu_grupo"]),
                            })

                        pdf_bytes  = generar_pdf_grupo(sesion_dict, est_list)
                        nombre_pdf = f"reporte_ACU_{group_safe}_{report.get('date', '')}.pdf"
                        zf.writestr(nombre_pdf, pdf_bytes)
                        pdf_incluido = True
                    else:
                        pdf_error = "El grupo necesita al menos 2 estudiantes para calcular el ACU."
                except Exception as e:
                    pdf_error = str(e)

            if pdf_incluido:
                mb.showinfo("Descarga completa",
                            f"ZIP guardado en:\n{save_path}\n\n✓ Incluye reporte PDF del ACU grupal.")
            else:
                msg = f"ZIP guardado en:\n{save_path}\n\n⚠ El PDF de ACU no se pudo generar."
                if pdf_error:
                    msg += f"\nDetalle: {pdf_error}"
                mb.showinfo("Descarga completa", msg)
        except Exception as exc:
            mb.showerror("Error", f"No se pudo crear el ZIP:\n{exc}")

    # ── Exportación Excel de grupo ────────────────────────────────────────────

    # ── Descarga PDF grupal ACU ───────────────────────────────────────────────

    def _download_group_pdf(self, report: dict):
        group_safe   = report.get("group_name", "grupo").replace(" ", "_")
        default_name = f"reporte_ACU_{group_safe}_{report.get('date', '')}.pdf"

        save_path = fd.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=default_name,
            title="Guardar reporte PDF del ACU grupal",
        )
        if not save_path:
            return

        try:
            records = fetch_group_records(report.get("id", ""))
            if not records:
                mb.showerror("Error", "No se encontraron registros para este reporte de grupo.")
                return

            from model.acu_engine import compute_acu
            from model.acu_pdf   import generar_pdf_grupo

            result = compute_acu(records)
            if not result:
                mb.showerror("Error",
                             "El grupo necesita al menos 2 estudiantes para calcular el ACU.")
                return

            mi  = result["model_info"]
            adf = result["acu_df"]

            sesion_dict = {
                "nombre_grupo":      report.get("group_name", "Grupo"),
                "fecha":             report.get("date",       ""),
                "hora":              report.get("time",       ""),
                "acu_promedio":      float(adf["ACU_%"].mean()),
                "total_estudiantes": int(len(adf)),
                "coef_b0":           mi["b0"],
                "coef_b1":           mi["b1"],
                "coef_b2":           mi["b2"],
                "coef_b3":           mi["b3"],
                "precision_modelo":  mi["precision"],
                "umbral_grupal":     mi["umbral"],
            }

            est_list = []
            for _, row in adf.iterrows():
                est_list.append({
                    "persona":              str(row["persona"]),
                    "preguntas":            int(row["preguntas"]),
                    "correctas":            int(row["correctas"]),
                    "incorrectas":          int(row["incorrectas"]),
                    "tasa_acierto":         float(row["tasa_acierto"]),
                    "tasa_acierto_pct":     float(row["tasa_acierto_%"]),
                    "emocion_predominante": str(row["emocion_predominante"]),
                    "confianza_media":      float(row["confianza_media"]),
                    "acu":                  float(row["ACU"]),
                    "acu_pct":              float(row["ACU_%"]),
                    "ranking":              int(row["ranking"]),
                    "total_alumnos":        int(row["total_alumnos"]),
                    "acu_grupo":            float(row["acu_grupo"]),
                })

            pdf_bytes = generar_pdf_grupo(sesion_dict, est_list)
            with open(save_path, "wb") as f:
                f.write(pdf_bytes)

            mb.showinfo("PDF generado", f"Reporte PDF guardado en:\n{save_path}")
        except Exception as exc:
            mb.showerror("Error", f"No se pudo generar el PDF:\n{exc}")

    # ── Exportación Excel de grupo ────────────────────────────────────────────

    def _export_group_excel(self, report: dict):
        records = fetch_group_records(report.get("id", ""))
        if not records:
            mb.showerror("Error", "No se encontraron registros para este reporte de grupo.")
            return

        group_safe   = report.get("group_name", "grupo").replace(" ", "_")
        default_name = f"grupo_{group_safe}_{report.get('date', '')}.xlsx"

        save_path = fd.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=default_name,
            title="Guardar reporte Excel del grupo",
        )
        if not save_path:
            return

        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Grupo"

            # Cabecera con fondo verde oscuro y texto blanco
            headers  = ["Persona", "Pregunta", "Respuesta (1/0)", "Respuesta correcta",
                        "Emoción", "Confianza (%)", "Timestamp"]
            hdr_fill = PatternFill("solid", fgColor="1a3a1a")
            hdr_font = Font(bold=True, color="FFFFFF")
            thin     = Side(style="thin", color="CCCCCC")
            border   = Border(left=thin, right=thin, top=thin, bottom=thin)

            for col, h in enumerate(headers, 1):
                cell           = ws.cell(row=1, column=col, value=h)
                cell.font      = hdr_font
                cell.fill      = hdr_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border    = border
            ws.row_dimensions[1].height = 20

            # Colores pastel claros por persona (legibles sobre fondo claro)
            person_colors = [
                "D6EAD6",  # verde pastel
                "D6E4F0",  # azul pastel
                "FFF3CD",  # amarillo pastel
                "F5D5E0",  # rosa pastel
                "E8D5F5",  # violeta pastel
                "D5F0EE",  # turquesa pastel
                "FFE0CC",  # naranja pastel
                "E0E0E0",  # gris pastel
            ]
            person_list  = report.get("persons", [])
            person_index = {p: i for i, p in enumerate(person_list)}

            for r_idx, rec in enumerate(records, 2):
                persona   = rec.get("persona", "")
                respondio = rec.get("respondio", "")
                is_true   = str(respondio).lower() in ("true", "1", "yes")

                valores = [
                    persona,
                    rec.get("pregunta", ""),
                    1 if is_true else 0,
                    rec.get("respuesta_correcta", "") if is_true else "",
                    rec.get("emocion", ""),
                    0,
                    str(rec.get("timestamp", "")),
                ]
                try:
                    valores[5] = round(float(rec.get("prob_emocion", 0)), 2)
                except (ValueError, TypeError):
                    pass

                p_idx    = person_index.get(persona, 0) % len(person_colors)
                row_fill = PatternFill("solid", fgColor=person_colors[p_idx])

                for col, val in enumerate(valores, 1):
                    cell           = ws.cell(row=r_idx, column=col, value=val)
                    cell.fill      = row_fill
                    cell.border    = border
                    cell.alignment = Alignment(vertical="center",
                                               horizontal="center" if col in (3, 5, 6, 7) else "left")
                    cell.font      = Font(color="000000")

            col_widths = [18, 46, 16, 38, 14, 14, 26]
            for col, width in enumerate(col_widths, 1):
                ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = width

            ws.freeze_panes = "A2"

            wb.save(save_path)
            mb.showinfo("Exportación completa", f"Excel del grupo guardado en:\n{save_path}")
        except ImportError:
            mb.showerror(
                "Módulo faltante",
                "Se requiere 'openpyxl' para exportar Excel.\n"
                "Instálalo con: pip install openpyxl",
            )
        except Exception as exc:
            mb.showerror("Error", f"No se pudo crear el Excel:\n{exc}")

    # ── Descarga ZIP individual ───────────────────────────────────────────────

    def _download(self, session: dict):
        sid          = session.get("id", "")
        session_dir  = session.get("dir", "")
        persona      = session.get("name", "sesion")
        name_safe    = persona.replace(" ", "_")
        default_name = f"reporte_{name_safe}_{session.get('date', '')}.zip"

        save_path = fd.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP file", "*.zip")],
            initialfile=default_name,
            title="Guardar reporte como ZIP",
        )
        if not save_path:
            return

        try:
            rows = self._fetch_registros(sid)

            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(["timestamp", "pregunta", "respuesta_correcta",
                              "emocion", "prob_emocion", "respondio", "imagen_path"])
            for row in rows:
                writer.writerow([
                    row.get("timestamp", ""),
                    row.get("pregunta", ""),
                    row.get("respuesta_correcta", ""),
                    row.get("emocion", ""),
                    row.get("prob_emocion", ""),
                    1 if row.get("respondio") else 0,
                    row.get("imagen_path", ""),
                ])

            with zipfile.ZipFile(save_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(f"{sid}/registros.csv", csv_buffer.getvalue())

                images_dir = os.path.join(session_dir, "images")
                if os.path.isdir(images_dir):
                    for fname in os.listdir(images_dir):
                        fpath = os.path.join(images_dir, fname)
                        zf.write(fpath, f"{sid}/images/{fname}")

                # Incluir PDF individual ACU si este estudiante tiene resultados en la BD
                try:
                    from model.acu_engine import fetch_acu_for_persona
                    from model.acu_pdf import generar_pdf_estudiante
                    est_data = fetch_acu_for_persona(persona)
                    if est_data:
                        pdf_bytes = generar_pdf_estudiante(
                            est_data,
                            nombre_grupo = str(est_data.get("nombre_grupo", "")),
                            fecha_sesion = str(est_data.get("fecha", ""))[:10],
                        )
                        zf.writestr(f"{sid}/reporte_ACU_{name_safe}.pdf", pdf_bytes)
                except Exception:
                    pass  # Si no hay ACU o falla el PDF, el CSV sigue estando

            mb.showinfo("Descarga completa", f"Reporte guardado en:\n{save_path}")
        except Exception as exc:
            mb.showerror("Error", f"No se pudo crear el ZIP:\n{exc}")
