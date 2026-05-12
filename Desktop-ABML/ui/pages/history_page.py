"""
ui/pages/history_page.py — Pantalla 4: Historial de sesiones.
"""
import os
import csv
import zipfile
import io
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import customtkinter as ctk
from PIL import Image

import ui.theme as T
from ui.assets import FLECHA_IZQ_FILE, USUARIO_FILE, REPORTE_FILE, DESCARGA_FILE, ELIMINAR_FILE
from ui.tooltip import Tooltip
from model.session_manager import load_sessions, delete_session
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
        self._ico_excel   = _load_icon(REPORTE_FILE,    T.GREEN_PRIMARY, size=24)
        self._ico_zip     = _load_icon(DESCARGA_FILE,   T.TEXT_LIGHT,    size=24)
        self._ico_delete  = _load_icon(ELIMINAR_FILE,   T.RED_PRIMARY,   size=22)

    # ── Construcción ─────────────────────────────────────────────────────────

    def _build(self):
        # Header
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

        # Título centrado
        title_f = ctk.CTkFrame(self, fg_color="transparent")
        title_f.pack(pady=(0, 10))
        ctk.CTkLabel(title_f, text="HISTORIAL",   text_color=T.GREEN_PRIMARY, font=T.bold(24)).pack(side="left")
        ctk.CTkLabel(title_f, text=" / USUARIOS", text_color=T.WHITE,         font=T.bold(24)).pack(side="left")

        sessions = load_sessions()

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=40, pady=(0, 6))

        if not sessions:
            ctk.CTkLabel(scroll, text="No hay análisis registrados aún.",
                         text_color=T.TEXT_DARKER, font=T.font(14)).pack(pady=40)
        else:
            for i, s in enumerate(reversed(sessions)):
                self._session_card(scroll, i + 1, s)

        ctk.CTkLabel(
            self,
            text=f"Total de análisis: {len(sessions)}",
            text_color=T.GREEN_PRIMARY, font=T.font(12),
        ).pack(pady=(0, 14))

    def _session_card(self, parent, num: int, session: dict):
        card = ctk.CTkFrame(parent, fg_color=T.BG_DARK, corner_radius=T.CORNER_RADIUS_CARD, height=T.HEIGHT_CARD)
        card.pack_propagate(False)
        card.pack(fill="x", pady=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=12, pady=10)

        # Badge de número
        badge = ctk.CTkFrame(inner, fg_color=T.BG_ICON_GREEN, corner_radius=10, width=34, height=34)
        badge.pack_propagate(False)
        badge.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(badge, text=str(num), text_color=T.GREEN_PRIMARY, font=T.bold(13)).pack(expand=True)

        # Ícono de usuario
        icon_box = ctk.CTkFrame(inner, fg_color=T.BG_GREEN_DIM, corner_radius=22, width=44, height=44)
        icon_box.pack_propagate(False)
        icon_box.pack(side="left", padx=(0, 12))
        if self._ico_usuario:
            ctk.CTkLabel(icon_box, image=self._ico_usuario, text="").pack(expand=True)

        # Info
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

        # Botones de descarga (solo icono)
        btns_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btns_frame.pack(side="right")

        btn_excel = ctk.CTkButton(
            btns_frame,
            text="", image=self._ico_excel,
            width=46, height=46,
            fg_color=T.BG_GREEN_DARK, hover_color=T.BG_GREEN_HOVER,
            corner_radius=T.CORNER_RADIUS_BTN,
            anchor="center",
            command=lambda s=session: self._export_excel(s),
        )
        btn_excel.pack(side="left", padx=(0, 6))
        Tooltip(btn_excel, "Descargar reporte Excel")

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

    def _fetch_registros(self, session_id: str) -> list:
        """Obtiene los registros de una sesión desde el API."""
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

    # ── Exportación Excel ─────────────────────────────────────────────────────

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
            from openpyxl.styles import Font, PatternFill, Alignment

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Resultados"

            headers = ["Pregunta", "Respuesta", "Respuesta correcta", "Emoción", "Confianza (%)", "Timestamp"]
            hdr_fill = PatternFill("solid", fgColor="1a3a1a")
            hdr_font = Font(bold=True, color="00e676")
            for col, h in enumerate(headers, 1):
                cell           = ws.cell(row=1, column=col, value=h)
                cell.font      = hdr_font
                cell.fill      = hdr_fill
                cell.alignment = Alignment(horizontal="center")

            for r_idx, row in enumerate(rows, 2):
                respondio      = row.get("respondio", False)
                correct_answer = row.get("respuesta_correcta", "") if respondio else ""

                ws.cell(row=r_idx, column=1, value=row.get("pregunta", ""))
                ws.cell(row=r_idx, column=2, value=1 if respondio else 0)
                ws.cell(row=r_idx, column=3, value=correct_answer)
                ws.cell(row=r_idx, column=4, value=row.get("emocion", ""))
                try:
                    ws.cell(row=r_idx, column=5, value=float(row.get("prob_emocion", 0)))
                except (ValueError, TypeError):
                    ws.cell(row=r_idx, column=5, value=0)
                ws.cell(row=r_idx, column=6, value=str(row.get("timestamp", "")))

                fill_color = "0d2b0d" if respondio else "2b0d0d"
                row_fill   = PatternFill("solid", fgColor=fill_color)
                for col in range(1, 7):
                    ws.cell(row=r_idx, column=col).fill = row_fill

            col_widths = [50, 12, 40, 18, 16, 28]
            for col, width in enumerate(col_widths, 1):
                ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = width

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

    # ── Descarga ZIP ──────────────────────────────────────────────────────────

    def _download(self, session: dict):
        sid          = session.get("id", "")
        session_dir  = session.get("dir", "")
        name_safe    = session.get("name", "sesion").replace(" ", "_")
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

            mb.showinfo("Descarga completa", f"Reporte guardado en:\n{save_path}")
        except Exception as exc:
            mb.showerror("Error", f"No se pudo crear el ZIP:\n{exc}")
