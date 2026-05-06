"""
ui/pages/setup_page.py — Pantalla 2: Configuración completa del análisis.

Dos pestañas:
  · Preguntas — Gestionar grupos de preguntas (TXT)
  · Personas  — Gestionar y seleccionar grupos de personas (TXT)

El análisis se inicia desde el footer una vez que hay un grupo de personas
seleccionado y al menos un banco de preguntas creado.
"""
import os
import random
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import customtkinter as ctk
from PIL import Image

import ui.theme as T
import ui.assets as A
from ui.tooltip import Tooltip
from model.groups_manager import (
    list_question_groups, save_question_group,
    delete_question_group, import_question_group_from_txt,
    list_person_groups, save_person_group,
    delete_person_group, import_person_group_from_txt,
)
from model.session_manager import create_session


# ═════════════════════════════════════════════════════════════════════════════
#  PÁGINA PRINCIPAL
# ═════════════════════════════════════════════════════════════════════════════

class SetupPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=T.BG_MAIN, corner_radius=0)
        self._app = app
        self._selected_person_group: dict | None = None
        self._tab_btns: dict[str, ctk.CTkButton] = {}
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _load_icon(path: str, hex_color: str, size: int = 18):
        if not os.path.exists(path):
            return None
        hi  = size * 2
        pil = Image.open(path).convert("RGBA").resize((hi, hi), Image.LANCZOS)
        r   = int(hex_color[1:3], 16)
        g   = int(hex_color[3:5], 16)
        b   = int(hex_color[5:7], 16)
        px  = pil.load()
        for y in range(pil.height):
            for x in range(pil.width):
                _, _, _, a = px[x, y]
                if a > 0:
                    px[x, y] = (r, g, b, a)
        return ctk.CTkImage(light_image=pil, dark_image=pil, size=(size, size))

    def _build(self):
        self._icon_back     = self._load_icon(A.FLECHA_IZQ_FILE, T.TEXT_MID,      18)
        self._icon_persona  = self._load_icon(A.PERSONA_FILE,   T.TEXT_LIGHT,    16)
        self._icon_pregunta = self._load_icon(A.PREGUNTA_FILE,   T.TEXT_LIGHT,    16)
        self._icon_mas      = self._load_icon(A.MAS_FILE,        T.GREEN_PRIMARY, 16)
        self._icon_importar = self._load_icon(A.IMPORTAR_FILE,   T.TEXT_LIGHT,    16)
        self._icon_editar   = self._load_icon(A.EDITAR_FILE,     T.TEXT_LIGHT,    14)
        self._icon_lecho    = self._load_icon(A.LECHO_FILE,      T.RED_PRIMARY,   14)
        self._icon_play     = self._load_icon(A.PLAY_FILE,       T.GREEN_PRIMARY, 18)
        self._build_header()
        self._build_tab_bar()

        # Footer fijo al fondo (se pack antes que content para que quede abajo)
        self._build_footer()

        # Área de contenido de las pestañas (rellena el espacio restante)
        self._content = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self._content.pack(fill="both", expand=True)

        self._tab_preguntas = self._build_tab_preguntas()
        self._tab_personas  = self._build_tab_personas()

        self._switch_tab("preguntas")
        self._validate_start()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 4))

        _back = ctk.CTkButton(
            header, image=self._icon_back, text="", width=42, height=42,
            fg_color=T.BG_CARD, hover_color=T.BG_HOVER,
            corner_radius=T.CORNER_RADIUS_BTN,
            command=self._app.show_main_menu,
        )
        _back.pack(side="left")
        Tooltip(_back, "Volver al menú principal")

        htxt = ctk.CTkFrame(header, fg_color="transparent")
        htxt.pack(side="left", padx=16)
        ctk.CTkLabel(htxt, text="Configuración del Análisis",
                     font=T.bold(20), text_color=T.WHITE).pack(anchor="w")
        ctk.CTkLabel(htxt, text="Gestiona grupos de preguntas y personas",
                     font=T.font(12), text_color=T.TEXT_DIM).pack(anchor="w")

    def _build_tab_bar(self):
        bar = ctk.CTkFrame(self, fg_color=T.BG_DARK, corner_radius=0, height=48)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(side="left", padx=20, fill="y")

        tab_defs = [
            ("preguntas", "  Preguntas", self._icon_pregunta),
            ("personas",  "  Personas",  self._icon_persona),
        ]
        for key, label, icon in tab_defs:
            kw = {"image": icon} if icon else {}
            btn = ctk.CTkButton(
                inner, text=label, height=36, width=148,
                fg_color="transparent", hover_color=T.BG_HOVER,
                text_color=T.TEXT_DIM, font=T.font(13), corner_radius=8,
                command=lambda k=key: self._switch_tab(k),
                **kw,
            )
            btn.pack(side="left", padx=2, pady=6)
            self._tab_btns[key] = btn

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=80, pady=(0, 16))

        self._start_btn = ctk.CTkButton(
            footer, image=self._icon_play, text="  Iniciar Análisis",
            height=T.HEIGHT_BTN_LG, fg_color=T.BG_BUTTON,
            hover_color=T.BG_BUTTON, text_color=T.TEXT_DIM,
            font=T.bold(15), corner_radius=T.CORNER_RADIUS_ENTRY,
            state="disabled", command=self._start_analysis,
        )
        self._start_btn.pack(fill="x")

        self._start_hint = ctk.CTkLabel(
            footer,
            text="Selecciona un grupo de personas en la pestaña 'Personas' para continuar",
            text_color=T.TEXT_DARKER, font=T.font(11),
        )
        self._start_hint.pack(pady=(6, 0))

    def _switch_tab(self, name: str):
        for k, btn in self._tab_btns.items():
            btn.configure(
                text_color=T.GREEN_PRIMARY if k == name else T.TEXT_DIM,
                fg_color=T.BG_GREEN_DIM if k == name else "transparent",
            )
        frames = {"preguntas": self._tab_preguntas, "personas": self._tab_personas}
        for k, tab in frames.items():
            tab.place(in_=self._content, relx=0, rely=0, relwidth=1, relheight=1)
            if k == name:
                tab.lift()
            else:
                tab.lower()

    # ─────────────────────────────────────────────────────────────────────────
    #  PESTAÑA 1 — PREGUNTAS
    # ─────────────────────────────────────────────────────────────────────────

    def _build_tab_preguntas(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self._content, fg_color="transparent", corner_radius=0)

        toolbar = ctk.CTkFrame(frame, fg_color="transparent")
        toolbar.pack(fill="x", padx=30, pady=(18, 8))
        ctk.CTkLabel(toolbar, text="Grupos de Preguntas",
                     font=T.bold(16), text_color=T.WHITE).pack(side="left")
        _imp_q = ctk.CTkButton(
            toolbar, image=self._icon_importar, text="  Importar TXT", height=36, width=160,
            fg_color=T.BG_BUTTON, hover_color=T.BG_HOVER,
            corner_radius=T.CORNER_RADIUS_BTN,
            text_color=T.TEXT_LIGHT, font=T.font(13),
            command=self._import_question_txt,
        )
        _imp_q.pack(side="right", padx=(6, 0))
        Tooltip(_imp_q, "Importar preguntas desde un archivo TXT")
        _crea_q = ctk.CTkButton(
            toolbar, image=self._icon_mas, text="  Crear Grupo", height=36, width=148,
            fg_color=T.BG_GREEN_DARK, hover_color=T.BG_GREEN_HOVER,
            corner_radius=T.CORNER_RADIUS_BTN,
            text_color=T.GREEN_PRIMARY, font=T.bold(13),
            command=self._open_create_question_dialog,
        )
        _crea_q.pack(side="right")
        Tooltip(_crea_q, "Crear un nuevo grupo de preguntas")

        ctk.CTkFrame(frame, fg_color=T.SEPARATOR, height=1).pack(fill="x", padx=30)

        self._q_list_frame = ctk.CTkScrollableFrame(
            frame, fg_color="transparent", corner_radius=0)
        self._q_list_frame.pack(fill="both", expand=True, padx=30, pady=(8, 20))

        self._refresh_questions_tab()
        return frame

    def _refresh_questions_tab(self):
        for w in self._q_list_frame.winfo_children():
            w.destroy()
        groups = list_question_groups()
        if not groups:
            ctk.CTkLabel(
                self._q_list_frame,
                text="No hay grupos de preguntas.\nCrea uno con '+ Crear Grupo' o importa un TXT.",
                font=T.font(14), text_color=T.TEXT_DIM, justify="center",
            ).pack(pady=50)
            self._validate_start()
            return
        for g in groups:
            self._make_q_card(g)
        self._validate_start()

    def _make_q_card(self, group: dict):
        card = ctk.CTkFrame(
            self._q_list_frame,
            fg_color=T.BG_CARD, corner_radius=T.CORNER_RADIUS_CARD, height=72,
        )
        card.pack(fill="x", pady=5)
        card.pack_propagate(False)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16)
        icon = ctk.CTkFrame(inner, fg_color=T.BG_ICON_GREEN,
                            corner_radius=8, width=36, height=36)
        icon.pack_propagate(False)
        icon.pack(side="left", pady=18)
        ctk.CTkLabel(icon, image=self._icon_pregunta, text="").place(
            relx=0.5, rely=0.5, anchor="center")
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", padx=12, fill="y", pady=12)
        ctk.CTkLabel(info, text=group["name"],
                     font=T.bold(14), text_color=T.WHITE).pack(anchor="w")
        ctk.CTkLabel(info, text=f"{len(group['questions'])} preguntas",
                     font=T.font(12), text_color=T.TEXT_DIM).pack(anchor="w")
        btns_q = ctk.CTkFrame(inner, fg_color="transparent")
        btns_q.pack(side="right", pady=18)
        _edit_q = ctk.CTkButton(
            btns_q, image=self._icon_editar, text="", width=36, height=36,
            fg_color=T.BG_BUTTON, hover_color=T.BG_HOVER, corner_radius=8,
            command=lambda g=group: self._edit_q_group(g),
        )
        _edit_q.pack(side="left", padx=(0, 4))
        Tooltip(_edit_q, "Editar grupo de preguntas")
        _del_q = ctk.CTkButton(
            btns_q, image=self._icon_lecho, text="", width=36, height=36,
            fg_color=T.BG_RED_DIM, hover_color="#4a0010", corner_radius=8,
            command=lambda g=group: self._delete_q_group(g["id"]),
        )
        _del_q.pack(side="left")
        Tooltip(_del_q, "Eliminar grupo")

    def _delete_q_group(self, group_id: int):
        delete_question_group(group_id)
        self._refresh_questions_tab()

    def _edit_q_group(self, group: dict):
        QuestionGroupDialog(self, on_save=self._refresh_questions_tab, existing=group)

    def _open_create_question_dialog(self):
        QuestionGroupDialog(self, on_save=self._refresh_questions_tab)

    def _import_question_txt(self):
        path = fd.askopenfilename(
            title="Importar grupo de preguntas",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos", "*.*")],
        )
        if not path:
            return
        try:
            import_question_group_from_txt(path)
            self._refresh_questions_tab()
        except ValueError as exc:
            mb.showerror("Formato incorrecto", str(exc))

    # ─────────────────────────────────────────────────────────────────────────
    #  PESTAÑA 2 — PERSONAS
    # ─────────────────────────────────────────────────────────────────────────

    def _build_tab_personas(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self._content, fg_color="transparent", corner_radius=0)

        toolbar = ctk.CTkFrame(frame, fg_color="transparent")
        toolbar.pack(fill="x", padx=30, pady=(18, 8))
        ctk.CTkLabel(toolbar, text="Grupos de Personas",
                     font=T.bold(16), text_color=T.WHITE).pack(side="left")
        _imp_p = ctk.CTkButton(
            toolbar, image=self._icon_importar, text="  Importar TXT", height=36, width=160,
            fg_color=T.BG_BUTTON, hover_color=T.BG_HOVER,
            corner_radius=T.CORNER_RADIUS_BTN,
            text_color=T.TEXT_LIGHT, font=T.font(13),
            command=self._import_people_txt,
        )
        _imp_p.pack(side="right", padx=(6, 0))
        Tooltip(_imp_p, "Importar personas desde un archivo TXT")
        _crea_p = ctk.CTkButton(
            toolbar, image=self._icon_mas, text="  Crear Grupo", height=36, width=148,
            fg_color=T.BG_GREEN_DARK, hover_color=T.BG_GREEN_HOVER,
            corner_radius=T.CORNER_RADIUS_BTN,
            text_color=T.GREEN_PRIMARY, font=T.bold(13),
            command=self._open_create_people_dialog,
        )
        _crea_p.pack(side="right")
        Tooltip(_crea_p, "Crear un nuevo grupo de personas")

        ctk.CTkFrame(frame, fg_color=T.SEPARATOR, height=1).pack(fill="x", padx=30)

        ctk.CTkLabel(
            frame,
            text="Selecciona el grupo que se usará al iniciar el análisis →",
            font=T.font(12), text_color=T.TEXT_DIM,
        ).pack(anchor="w", padx=30, pady=(8, 0))

        self._p_list_frame = ctk.CTkScrollableFrame(
            frame, fg_color="transparent", corner_radius=0)
        self._p_list_frame.pack(fill="both", expand=True, padx=30, pady=(6, 12))

        self._refresh_people_tab()
        return frame

    def _refresh_people_tab(self):
        for w in self._p_list_frame.winfo_children():
            w.destroy()
        groups = list_person_groups()
        if not groups:
            ctk.CTkLabel(
                self._p_list_frame,
                text="No hay grupos de personas.\nCrea uno con '+ Crear Grupo' o importa un TXT.",
                font=T.font(14), text_color=T.TEXT_DIM, justify="center",
            ).pack(pady=50)
            self._validate_start()
            return
        for g in groups:
            self._make_p_card(g)
        self._validate_start()

    def _make_p_card(self, group: dict):
        is_sel = (
            self._selected_person_group is not None
            and self._selected_person_group.get("id") == group["id"]
        )
        card = ctk.CTkFrame(
            self._p_list_frame,
            fg_color=T.BG_GREEN_DIM if is_sel else T.BG_CARD,
            corner_radius=T.CORNER_RADIUS_CARD, height=72,
            border_color=T.GREEN_PRIMARY if is_sel else T.BG_CARD,
            border_width=1,
        )
        card.pack(fill="x", pady=5)
        card.pack_propagate(False)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16)
        icon = ctk.CTkFrame(inner, fg_color=T.BG_ICON_GREEN,
                            corner_radius=8, width=36, height=36)
        icon.pack_propagate(False)
        icon.pack(side="left", pady=18)
        ctk.CTkLabel(icon, image=self._icon_persona, text="").place(
            relx=0.5, rely=0.5, anchor="center")
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", padx=12, fill="y", pady=12)
        ctk.CTkLabel(info, text=group["name"], font=T.bold(14),
                     text_color=T.GREEN_PRIMARY if is_sel else T.WHITE).pack(anchor="w")
        extra = "  · Seleccionado ✓" if is_sel else ""
        ctk.CTkLabel(info, text=f"{len(group['people'])} personas{extra}",
                     font=T.font(12),
                     text_color=T.GREEN_PRIMARY if is_sel else T.TEXT_DIM).pack(anchor="w")
        btns = ctk.CTkFrame(inner, fg_color="transparent")
        btns.pack(side="right", pady=18)
        ctk.CTkButton(
            btns,
            text="✓ Activo" if is_sel else "Seleccionar",
            width=100, height=34,
            fg_color=T.BG_ICON_GREEN if is_sel else T.BG_GREEN_DARK,
            hover_color=T.BG_GREEN_HOVER,
            text_color=T.GREEN_PRIMARY, font=T.bold(12), corner_radius=8,
            command=lambda g=group: self._select_person_group(g),
        ).pack(side="left", padx=(0, 4))
        _edit_p = ctk.CTkButton(
            btns, image=self._icon_editar, text="", width=36, height=34,
            fg_color=T.BG_BUTTON, hover_color=T.BG_HOVER, corner_radius=8,
            command=lambda g=group: self._edit_p_group(g),
        )
        _edit_p.pack(side="left", padx=(0, 4))
        Tooltip(_edit_p, "Editar grupo de personas")
        _del_p = ctk.CTkButton(
            btns, image=self._icon_lecho, text="", width=36, height=34,
            fg_color=T.BG_RED_DIM, hover_color="#4a0010", corner_radius=8,
            command=lambda gid=group["id"]: self._delete_p_group(gid),
        )
        _del_p.pack(side="left")
        Tooltip(_del_p, "Eliminar grupo")

    def _select_person_group(self, group: dict):
        self._selected_person_group = group
        self._refresh_people_tab()
        # _validate_start() is called inside _refresh_people_tab

    def _delete_p_group(self, group_id: int):
        if self._selected_person_group and self._selected_person_group.get("id") == group_id:
            self._selected_person_group = None
        delete_person_group(group_id)
        self._refresh_people_tab()

    def _edit_p_group(self, group: dict):
        PersonGroupDialog(self, on_save=self._refresh_people_tab, existing=group)

    def _open_create_people_dialog(self):
        PersonGroupDialog(self, on_save=self._refresh_people_tab)

    def _import_people_txt(self):
        path = fd.askopenfilename(
            title="Importar grupo de personas",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos", "*.*")],
        )
        if path:
            import_person_group_from_txt(path)
            self._refresh_people_tab()

    # ─────────────────────────────────────────────────────────────────────────
    #  FOOTER — INICIO DEL ANÁLISIS
    # ─────────────────────────────────────────────────────────────────────────

    def _validate_start(self):
        has_people = self._selected_person_group is not None
        has_banks  = len(list_question_groups()) > 0

        if has_people and has_banks:
            self._start_btn.configure(
                state="normal", fg_color=T.BG_GREEN_DARK,
                hover_color=T.BG_GREEN_HOVER, text_color=T.GREEN_PRIMARY,
            )
            self._start_hint.configure(
                text=f"Grupo seleccionado: {self._selected_person_group['name']}  ·  Las preguntas se sortearán aleatoriamente",
                text_color=T.TEXT_DIM,
            )
        else:
            self._start_btn.configure(
                state="disabled", fg_color=T.BG_BUTTON, text_color=T.TEXT_DIM,
            )
            if not has_banks:
                hint = "Crea al menos un banco de preguntas en la pestaña 'Preguntas'"
            elif not has_people:
                hint = "Selecciona un grupo de personas en la pestaña 'Personas' para continuar"
            else:
                hint = "Completa la configuración para continuar"
            self._start_hint.configure(text=hint, text_color=T.TEXT_DARKER)

    def _start_analysis(self):
        if not self._selected_person_group:
            return

        q_groups = list_question_groups()
        if not q_groups:
            return

        # Usar el primer banco de preguntas disponible (el usuario puede cambiarlo en el análisis)
        g          = q_groups[0]
        all_people = self._selected_person_group.get("people", [])
        if not all_people:
            return

        first_person = all_people[0]
        n            = min(5, len(g["questions"]))
        # random.sample garantiza no repetición DENTRO de la sesión
        selected_qs  = random.sample(g["questions"], n)

        context = {
            "person_group":        all_people,
            "current_person_idx":  0,
            "q_group_name":        g["name"],
            "n_questions":         n,
        }

        session = create_session(first_person, selected_qs, question_group=g["name"])
        self._app.show_analysis(session, context)


# ═════════════════════════════════════════════════════════════════════════════
#  DIÁLOGO — CREAR GRUPO DE PREGUNTAS
# ═════════════════════════════════════════════════════════════════════════════

class QuestionGroupDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_save, existing: dict = None):
        super().__init__(parent)
        self._existing = existing
        self.title("Editar Grupo de Preguntas" if existing else "Crear Grupo de Preguntas")
        self.geometry("660x700")
        self.configure(fg_color=T.BG_MAIN)
        self.resizable(False, True)
        self.grab_set()
        self._on_save = on_save
        self._q_rows: list[dict] = []
        self._icon_mas        = SetupPage._load_icon(A.MAS_FILE,      T.GREEN_PRIMARY, 14)
        self._icon_disquete   = SetupPage._load_icon(A.DISQUETE_FILE, T.GREEN_PRIMARY, 16)
        self._icon_borrar     = SetupPage._load_icon(A.BORRAR_FILE,   T.TEXT_MID,      14)
        self._icon_borrar_red = SetupPage._load_icon(A.BORRAR_FILE,   T.RED_PRIMARY,   13)
        self._icon_borrar_dim = SetupPage._load_icon(A.BORRAR_FILE,   T.TEXT_DARKER,   11)
        self._build()
        self.focus_force()
        self.after(200, lambda: self.iconbitmap(A.APP_ICO_FILE))

    def _build(self):
        h = ctk.CTkFrame(self, fg_color=T.BG_DARK, corner_radius=0, height=60)
        h.pack(fill="x")
        h.pack_propagate(False)
        ih = ctk.CTkFrame(h, fg_color="transparent")
        ih.pack(fill="both", expand=True, padx=20)
        title_txt = "Editar Grupo de Preguntas" if self._existing else "Nuevo Grupo de Preguntas"
        ctk.CTkLabel(ih, text=title_txt,
                     font=T.bold(16), text_color=T.WHITE).pack(side="left", pady=10)
        _close_btn = ctk.CTkButton(
            ih, image=self._icon_borrar, text="", width=32, height=32,
            fg_color="transparent", hover_color=T.BG_HOVER,
            corner_radius=8, command=self.destroy,
        )
        _close_btn.pack(side="right", pady=14)
        Tooltip(_close_btn, "Cerrar sin guardar")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=16)

        ctk.CTkLabel(body, text="Nombre del grupo",
                     font=T.bold(13), text_color=T.TEXT_LIGHT).pack(anchor="w", pady=(0, 4))
        self._name_entry = ctk.CTkEntry(
            body, placeholder_text="Ej: Tipos de datos",
            height=T.HEIGHT_ENTRY, fg_color=T.BG_DARK, border_color=T.BG_BUTTON,
            text_color=T.TEXT_LIGHT, placeholder_text_color=T.TEXT_DARKER,
            font=T.font(14), corner_radius=T.CORNER_RADIUS_ENTRY,
        )
        self._name_entry.pack(fill="x", pady=(0, 12))
        if self._existing:
            self._name_entry.insert(0, self._existing["name"])

        qh = ctk.CTkFrame(body, fg_color="transparent")
        qh.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(qh, text="Preguntas",
                     font=T.bold(13), text_color=T.TEXT_LIGHT).pack(side="left")
        _add_q_btn = ctk.CTkButton(
            qh, image=self._icon_mas, text="  Agregar Pregunta", width=158, height=30,
            fg_color=T.BG_GREEN_DARK, hover_color=T.BG_GREEN_HOVER,
            corner_radius=8, text_color=T.GREEN_PRIMARY, font=T.bold(12),
            command=self._add_row,
        )
        _add_q_btn.pack(side="right")
        Tooltip(_add_q_btn, "Agregar una nueva pregunta")

        self._q_scroll = ctk.CTkScrollableFrame(
            body, fg_color=T.BG_DARK, corner_radius=8, height=370)
        self._q_scroll.pack(fill="x", pady=(0, 12))

        if self._existing and self._existing.get("questions"):
            for q in self._existing["questions"]:
                val = q if isinstance(q, dict) else {"text": q, "options": [], "correct": -1}
                self._add_row(value=val)
        else:
            self._add_row()

        foot = ctk.CTkFrame(body, fg_color="transparent")
        foot.pack(fill="x")
        _cancel_btn = ctk.CTkButton(
            foot, text="Cancelar", height=46, width=120,
            fg_color=T.BG_BUTTON, hover_color=T.BG_HOVER,
            corner_radius=T.CORNER_RADIUS_BTN,
            text_color=T.TEXT_MID, font=T.font(13), command=self.destroy,
        )
        _cancel_btn.pack(side="left")
        Tooltip(_cancel_btn, "Cancelar sin guardar")
        _save_btn = ctk.CTkButton(
            foot, image=self._icon_disquete,
            text="  Guardar Cambios" if self._existing else "  Guardar Grupo",
            height=46,
            fg_color=T.BG_GREEN_DARK, hover_color=T.BG_GREEN_HOVER,
            corner_radius=T.CORNER_RADIUS_BTN,
            text_color=T.GREEN_PRIMARY, font=T.bold(13), command=self._save,
        )
        _save_btn.pack(side="right")
        Tooltip(_save_btn, "Guardar el grupo de preguntas")

    def _add_row(self, value: dict = None):
        if value is None:
            value = {"text": "", "options": [], "correct": -1}
        q_idx = len(self._q_rows) + 1

        card = ctk.CTkFrame(self._q_scroll, fg_color=T.BG_CARD, corner_radius=8)
        card.pack(fill="x", pady=4, padx=2)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(
            top, text=str(q_idx), width=26, height=32,
            fg_color=T.BG_DARK, corner_radius=6,
            text_color=T.TEXT_MID, font=T.bold(12),
        ).pack(side="left", padx=(0, 8))

        text_entry = ctk.CTkEntry(
            top, placeholder_text=f"Pregunta {q_idx}…",
            height=34, fg_color=T.BG_DARK, border_color=T.BG_HOVER,
            text_color=T.TEXT_LIGHT, placeholder_text_color=T.TEXT_DARKER,
            font=T.font(13), corner_radius=6,
        )
        if value.get("text"):
            text_entry.insert(0, value["text"])

        row_dict = {
            "frame":         card,
            "text_entry":    text_entry,
            "opt_entries":   [],
            "opt_frames":    [],
            "opt_btns":      [],
            "del_opt_btns":  [],
            "correct_entry": [None],
            "opts_frame":    None,
            "add_opt_btn":   None,
        }

        del_q_btn = ctk.CTkButton(
            top, image=self._icon_borrar_red, text="", width=28, height=32,
            fg_color=T.BG_RED_DIM, hover_color="#4a0010", corner_radius=6,
            command=lambda c=card, r=row_dict: self._del_row(c, r),
        )
        del_q_btn.pack(side="right")
        Tooltip(del_q_btn, "Eliminar esta pregunta")
        text_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        # Options header
        opts_hdr = ctk.CTkFrame(card, fg_color="transparent")
        opts_hdr.pack(fill="x", padx=8, pady=(0, 2))
        ctk.CTkLabel(
            opts_hdr, text="Opciones de respuesta:",
            font=T.font(11), text_color=T.TEXT_DIM,
        ).pack(side="left", padx=(28, 0))
        _add_opt_btn = ctk.CTkButton(
            opts_hdr, image=self._icon_mas, text="  Opción", width=90, height=24,
            fg_color=T.BG_ICON_GREEN, hover_color="#243a24",
            corner_radius=6, text_color=T.GREEN_PRIMARY, font=T.font(11),
            command=lambda r=row_dict: self._add_option(r),
        )
        _add_opt_btn.pack(side="right")
        Tooltip(_add_opt_btn, "Agregar opción de respuesta (máx. 4)")
        row_dict["add_opt_btn"] = _add_opt_btn

        opts_frame = ctk.CTkFrame(card, fg_color="transparent")
        opts_frame.pack(fill="x", padx=8, pady=(0, 8))
        row_dict["opts_frame"] = opts_frame

        # Cargar opciones existentes y asegurar mínimo 2
        options     = value.get("options", [])
        correct_idx = value.get("correct", -1)
        for opt_text in options:
            self._add_option(row_dict, opt_text)
        while len(row_dict["opt_entries"]) < 2:
            self._add_option(row_dict)
        if 0 <= correct_idx < len(row_dict["opt_entries"]):
            row_dict["correct_entry"][0] = row_dict["opt_entries"][correct_idx]
            self._refresh_opt_btns(row_dict)

        self._update_opt_controls(row_dict)
        self._q_rows.append(row_dict)

    def _add_option(self, row_dict: dict, value: str = ""):
        if len(row_dict["opt_entries"]) >= 4:
            return
        idx     = len(row_dict["opt_entries"])
        letters = "ABCDEFGHIJKLMNOP"
        letter  = letters[idx] if idx < len(letters) else str(idx + 1)

        opt_frame = ctk.CTkFrame(row_dict["opts_frame"], fg_color="transparent")
        opt_frame.pack(fill="x", pady=1, padx=(28, 0))

        # Create entry first (without packing) so indicator closure captures it
        opt_entry = ctk.CTkEntry(
            opt_frame, placeholder_text=f"Opción {letter}…",
            height=30, fg_color=T.BG_DARK, border_color=T.BG_HOVER,
            text_color=T.TEXT_LIGHT, placeholder_text_color=T.TEXT_DARKER,
            font=T.font(12), corner_radius=6,
        )
        if value:
            opt_entry.insert(0, value)

        indicator = ctk.CTkButton(
            opt_frame, text="○", width=28, height=28,
            fg_color="transparent", hover_color=T.BG_HOVER,
            text_color=T.TEXT_DARKER, font=T.bold(14), corner_radius=14,
            command=lambda e=opt_entry: self._set_correct(row_dict, e),
        )
        Tooltip(indicator, "Marcar como respuesta correcta")

        del_opt_btn = ctk.CTkButton(
            opt_frame, image=self._icon_borrar_dim, text="", width=24, height=28,
            fg_color="transparent", hover_color=T.BG_RED_DIM, corner_radius=6,
            command=lambda f=opt_frame, e=opt_entry, b=indicator: self._del_option(row_dict, f, e, b),
        )
        Tooltip(del_opt_btn, "Eliminar esta opción")

        indicator.pack(side="left", padx=(0, 2))
        ctk.CTkLabel(
            opt_frame, text=f"{letter}.", width=16,
            text_color=T.TEXT_MID, font=T.bold(11),
        ).pack(side="left", padx=(0, 4))
        del_opt_btn.pack(side="right")
        opt_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        row_dict["opt_entries"].append(opt_entry)
        row_dict["opt_frames"].append(opt_frame)
        row_dict["opt_btns"].append(indicator)
        row_dict["del_opt_btns"].append(del_opt_btn)
        self._update_opt_controls(row_dict)

    def _set_correct(self, row_dict: dict, entry):
        if row_dict["correct_entry"][0] is entry:
            row_dict["correct_entry"][0] = None
        else:
            row_dict["correct_entry"][0] = entry
        self._refresh_opt_btns(row_dict)

    def _refresh_opt_btns(self, row_dict: dict):
        for btn, entry in zip(row_dict["opt_btns"], row_dict["opt_entries"]):
            is_correct = (entry is row_dict["correct_entry"][0])
            btn.configure(
                text="●" if is_correct else "○",
                text_color=T.GREEN_PRIMARY if is_correct else T.TEXT_DARKER,
            )

    def _del_option(self, row_dict: dict, opt_frame, opt_entry, indicator):
        if len(row_dict["opt_entries"]) <= 2:
            return
        if row_dict["correct_entry"][0] is opt_entry:
            row_dict["correct_entry"][0] = None
        if opt_entry in row_dict["opt_entries"]:
            i = row_dict["opt_entries"].index(opt_entry)
            row_dict["opt_entries"].pop(i)
            row_dict["opt_frames"].pop(i)
            row_dict["opt_btns"].pop(i)
            row_dict["del_opt_btns"].pop(i)
        opt_frame.destroy()
        self._update_opt_controls(row_dict)

    def _update_opt_controls(self, row_dict: dict):
        count   = len(row_dict["opt_entries"])
        add_btn = row_dict.get("add_opt_btn")
        if add_btn:
            if count >= 4:
                add_btn.configure(state="disabled", fg_color="#0d1a0d",
                                  text_color=T.TEXT_DIM)
            else:
                add_btn.configure(state="normal", fg_color=T.BG_ICON_GREEN,
                                  text_color=T.GREEN_PRIMARY)
        can_del = count > 2
        for db in row_dict.get("del_opt_btns", []):
            db.configure(state="normal" if can_del else "disabled")

    def _del_row(self, card, row_dict: dict):
        if row_dict in self._q_rows:
            self._q_rows.remove(row_dict)
        card.destroy()

    def _save(self):
        name      = self._name_entry.get().strip()
        questions = []
        for row in self._q_rows:
            text = row["text_entry"].get().strip()
            if not text:
                continue
            valid_pairs = [
                (e.get().strip(), e)
                for e in row["opt_entries"]
                if e.get().strip()
            ]
            if len(valid_pairs) < 2:
                continue
            options       = [t for t, _ in valid_pairs]
            correct_entry = row["correct_entry"][0]
            correct       = -1
            for i, (_, e) in enumerate(valid_pairs):
                if e is correct_entry:
                    correct = i
                    break
            questions.append({"text": text, "options": options, "correct": correct})

        if not name:
            self._show_error("Escribe un nombre para el grupo.")
            return
        if len(questions) < 2:
            self._show_error("Se necesitan al menos 2 preguntas con texto y 2 opciones cada una.")
            return
        if self._existing:
            delete_question_group(self._existing["id"])
        save_question_group(name, questions)
        self._on_save()
        self.destroy()

    def _show_error(self, msg: str):
        if hasattr(self, "_err_lbl") and self._err_lbl.winfo_exists():
            self._err_lbl.configure(text=msg)
        else:
            self._err_lbl = ctk.CTkLabel(
                self, text=msg, font=T.font(11), text_color=T.RED_PRIMARY,
            )
            self._err_lbl.pack(pady=(0, 6))
        self.after(3500, lambda: self._err_lbl.destroy()
                   if hasattr(self, "_err_lbl") and self._err_lbl.winfo_exists() else None)


# ═════════════════════════════════════════════════════════════════════════════
#  DIÁLOGO — CREAR GRUPO DE PERSONAS
# ═════════════════════════════════════════════════════════════════════════════

class PersonGroupDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_save, existing: dict = None):
        super().__init__(parent)
        self._existing = existing
        self.title("Editar Grupo de Personas" if existing else "Crear Grupo de Personas")
        self.geometry("600x530")
        self.configure(fg_color=T.BG_MAIN)
        self.resizable(False, True)
        self.grab_set()
        self._on_save = on_save
        self._p_rows: list[ctk.CTkEntry] = []
        self._icon_mas      = SetupPage._load_icon(A.MAS_FILE,      T.GREEN_PRIMARY, 14)
        self._icon_disquete = SetupPage._load_icon(A.DISQUETE_FILE, T.GREEN_PRIMARY, 16)
        self._icon_borrar   = SetupPage._load_icon(A.BORRAR_FILE,   T.TEXT_MID,      14)
        self._build()
        self.focus_force()
        self.after(200, lambda: self.iconbitmap(A.APP_ICO_FILE))

    def _build(self):
        h = ctk.CTkFrame(self, fg_color=T.BG_DARK, corner_radius=0, height=60)
        h.pack(fill="x")
        h.pack_propagate(False)
        ih = ctk.CTkFrame(h, fg_color="transparent")
        ih.pack(fill="both", expand=True, padx=20)
        title_txt = "Editar Grupo de Personas" if self._existing else "Nuevo Grupo de Personas"
        ctk.CTkLabel(ih, text=title_txt,
                     font=T.bold(16), text_color=T.WHITE).pack(side="left", pady=10)
        _close_btn_p = ctk.CTkButton(
            ih, image=self._icon_borrar, text="", width=32, height=32,
            fg_color="transparent", hover_color=T.BG_HOVER,
            corner_radius=8, command=self.destroy,
        )
        _close_btn_p.pack(side="right", pady=14)
        Tooltip(_close_btn_p, "Cerrar sin guardar")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=16)

        ctk.CTkLabel(body, text="Nombre del grupo",
                     font=T.bold(13), text_color=T.TEXT_LIGHT).pack(anchor="w", pady=(0, 4))
        self._name_entry = ctk.CTkEntry(
            body, placeholder_text="Ej: Estudiantes 2024",
            height=T.HEIGHT_ENTRY, fg_color=T.BG_DARK, border_color=T.BG_BUTTON,
            text_color=T.TEXT_LIGHT, placeholder_text_color=T.TEXT_DARKER,
            font=T.font(14), corner_radius=T.CORNER_RADIUS_ENTRY,
        )
        self._name_entry.pack(fill="x", pady=(0, 16))
        if self._existing:
            self._name_entry.insert(0, self._existing["name"])

        ph = ctk.CTkFrame(body, fg_color="transparent")
        ph.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(ph, text="Personas",
                     font=T.bold(13), text_color=T.TEXT_LIGHT).pack(side="left")
        _add_p_btn = ctk.CTkButton(
            ph, image=self._icon_mas, text="  Agregar", width=112, height=30,
            fg_color=T.BG_GREEN_DARK, hover_color=T.BG_GREEN_HOVER,
            corner_radius=8, text_color=T.GREEN_PRIMARY, font=T.bold(12),
            command=self._add_row,
        )
        _add_p_btn.pack(side="right")
        Tooltip(_add_p_btn, "Agregar una nueva persona")

        self._p_scroll = ctk.CTkScrollableFrame(
            body, fg_color=T.BG_DARK, corner_radius=8, height=200)
        self._p_scroll.pack(fill="x", pady=(0, 16))

        # Poblar con existentes o añadir una fila vacía
        if self._existing and self._existing.get("people"):
            for p in self._existing["people"]:
                self._add_row(value=p)
        else:
            self._add_row()

        foot = ctk.CTkFrame(body, fg_color="transparent")
        foot.pack(fill="x")
        _cancel_btn_p = ctk.CTkButton(
            foot, text="Cancelar", height=46, width=120,
            fg_color=T.BG_BUTTON, hover_color=T.BG_HOVER,
            corner_radius=T.CORNER_RADIUS_BTN,
            text_color=T.TEXT_MID, font=T.font(13), command=self.destroy,
        )
        _cancel_btn_p.pack(side="left")
        Tooltip(_cancel_btn_p, "Cancelar sin guardar")
        _save_btn_p = ctk.CTkButton(
            foot, image=self._icon_disquete,
            text="  Guardar Cambios" if self._existing else "  Guardar Grupo",
            height=46,
            fg_color=T.BG_GREEN_DARK, hover_color=T.BG_GREEN_HOVER,
            corner_radius=T.CORNER_RADIUS_BTN,
            text_color=T.GREEN_PRIMARY, font=T.bold(13), command=self._save,
        )
        _save_btn_p.pack(side="right")
        Tooltip(_save_btn_p, "Guardar el grupo de personas")

    def _add_row(self, value: str = ""):
        idx = len(self._p_rows) + 1
        row = ctk.CTkFrame(self._p_scroll, fg_color="transparent")
        row.pack(fill="x", pady=3)
        ctk.CTkLabel(
            row, text=str(idx), width=28, height=34,
            fg_color=T.BG_CARD, corner_radius=6,
            text_color=T.TEXT_MID, font=T.bold(12),
        ).pack(side="left", padx=(4, 8))
        entry = ctk.CTkEntry(
            row, placeholder_text=f"Nombre persona {idx}…",
            height=38, fg_color=T.BG_BUTTON, border_color=T.BG_HOVER,
            text_color=T.TEXT_LIGHT, placeholder_text_color=T.TEXT_DARKER,
            font=T.font(13), corner_radius=8,
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        if value:
            entry.insert(0, value)
        self._p_rows.append(entry)

    def _save(self):
        name   = self._name_entry.get().strip()
        people = [e.get().strip() for e in self._p_rows if e.get().strip()]
        if not name or not people:
            return
        if self._existing:
            delete_person_group(self._existing["id"])
        save_person_group(name, people)
        self._on_save()
        self.destroy()


# ═════════════════════════════════════════════════════════════════════════════
#  HELPER — COMBO DE SOLO LECTURA
# ═════════════════════════════════════════════════════════════════════════════

def _make_readonly(combo: ctk.CTkComboBox) -> None:
    """Bloquea la escritura de teclado en un CTkComboBox sin deshabilitar el dropdown."""
    try:
        combo._entry.bind("<Key>",       lambda e: "break")
        combo._entry.bind("<BackSpace>", lambda e: "break")
        combo._entry.bind("<Delete>",    lambda e: "break")
    except Exception:
        pass
