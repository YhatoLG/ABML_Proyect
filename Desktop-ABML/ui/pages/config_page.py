"""
ui/pages/config_page.py — Pantalla 2: Configuración del análisis.
"""
import customtkinter as ctk

import ui.theme as T
from model.session_manager import create_session


class ConfigPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=T.BG_MAIN, corner_radius=0)
        self._app      = app
        self._q_entries: list[ctk.CTkEntry] = []
        self._build()

    # ── Construcción ─────────────────────────────────────────────────────────

    def _build(self):
        self._build_header()
        self._build_body()
        self._build_footer()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 4))

        ctk.CTkButton(
            header, text="←", width=42, height=42,
            fg_color=T.BG_CARD, hover_color=T.BG_HOVER, corner_radius=T.CORNER_RADIUS_BTN,
            text_color=T.TEXT_MID, font=T.font(16),
            command=self._app.show_main_menu,
        ).pack(side="left")

        htxt = ctk.CTkFrame(header, fg_color="transparent")
        htxt.pack(side="left", padx=16)
        ctk.CTkLabel(htxt, text="Configuración del Análisis",
                     font=T.bold(20), text_color=T.WHITE).pack(anchor="w")
        ctk.CTkLabel(htxt, text="Ingresa los datos antes de iniciar",
                     font=T.font(12), text_color=T.TEXT_DIM).pack(anchor="w")

    def _build_body(self):
        body = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        body.pack(fill="both", expand=True, padx=100, pady=6)

        # Sección sujeto
        sh = ctk.CTkFrame(body, fg_color="transparent")
        sh.pack(fill="x", pady=(10, 8))
        ib = ctk.CTkFrame(sh, fg_color=T.BG_ICON_GREEN, corner_radius=8, width=32, height=32)
        ib.pack_propagate(False)
        ib.pack(side="left")
        ctk.CTkLabel(ib, text="👤", font=T.font(15)).place(relx=0.5, rely=0.5, anchor="center")
        st = ctk.CTkFrame(sh, fg_color="transparent")
        st.pack(side="left", padx=10)
        ctk.CTkLabel(st, text="Datos del Sujeto",                  text_color=T.WHITE,    font=T.bold(14)).pack(anchor="w")
        ctk.CTkLabel(st, text="Información de la persona a analizar", text_color=T.TEXT_DIM, font=T.font(11)).pack(anchor="w")

        self.name_entry = ctk.CTkEntry(
            body, placeholder_text="Nombre completo de la persona",
            height=T.HEIGHT_ENTRY, fg_color=T.BG_DARK, border_color=T.BG_BUTTON,
            text_color=T.TEXT_LIGHT, placeholder_text_color=T.TEXT_DARKER,
            font=T.font(14), corner_radius=T.CORNER_RADIUS_ENTRY,
        )
        self.name_entry.pack(fill="x", pady=(0, 18))
        self.name_entry.bind("<KeyRelease>", lambda e: self._validate())

        # Sección preguntas
        qh = ctk.CTkFrame(body, fg_color="transparent")
        qh.pack(fill="x", pady=(0, 8))
        ib2 = ctk.CTkFrame(qh, fg_color="#2a1010", corner_radius=8, width=32, height=32)
        ib2.pack_propagate(False)
        ib2.pack(side="left")
        ctk.CTkLabel(ib2, text="💬", font=T.font(15)).place(relx=0.5, rely=0.5, anchor="center")
        qt = ctk.CTkFrame(qh, fg_color="transparent")
        qt.pack(side="left", padx=10)
        ctk.CTkLabel(qt, text="Preguntas para el Análisis",                              text_color=T.WHITE,    font=T.bold(14)).pack(anchor="w")
        ctk.CTkLabel(qt, text="Define las preguntas que se realizarán durante la sesión", text_color=T.TEXT_DIM, font=T.font(11)).pack(anchor="w")

        self.q_frame = ctk.CTkFrame(body, fg_color="transparent")
        self.q_frame.pack(fill="x")
        self._add_question()

        ctk.CTkButton(
            body, text="+ Agregar más preguntas",
            fg_color="transparent", hover_color=T.BG_DARK,
            border_color=T.BG_HOVER, border_width=1,
            text_color=T.TEXT_DIM, font=T.font(13),
            corner_radius=12, height=48,
            command=self._add_question,
        ).pack(fill="x", pady=(4, 16))

    def _build_footer(self):
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=100, pady=(0, 18))

        self.start_btn = ctk.CTkButton(
            bottom, text="▷  Iniciar Análisis",
            height=T.HEIGHT_BTN_LG, fg_color=T.BG_BUTTON, hover_color=T.BG_BUTTON,
            text_color=T.TEXT_DIM, font=T.bold(15),
            corner_radius=T.CORNER_RADIUS_ENTRY, state="disabled",
            command=self._start,
        )
        self.start_btn.pack(fill="x")

        self.hint_lbl = ctk.CTkLabel(
            bottom,
            text="Completa el nombre y al menos una pregunta para continuar",
            text_color=T.TEXT_DARKER, font=T.font(11),
        )
        self.hint_lbl.pack(pady=(6, 0))

    # ── Lógica ────────────────────────────────────────────────────────────────

    def _add_question(self):
        idx = len(self._q_entries) + 1
        row = ctk.CTkFrame(self.q_frame, fg_color="transparent")
        row.pack(fill="x", pady=3)

        ctk.CTkLabel(
            row, text=str(idx), width=34, height=34,
            fg_color=T.BG_CARD, corner_radius=8,
            text_color=T.TEXT_MID, font=T.bold(13),
        ).pack(side="left", padx=(0, 8))

        entry = ctk.CTkEntry(
            row, placeholder_text=f"Escribe la pregunta {idx}...",
            height=T.HEIGHT_BTN_MD, fg_color=T.BG_DARK, border_color=T.BG_BUTTON,
            text_color=T.TEXT_LIGHT, placeholder_text_color="#333333",
            font=T.font(13), corner_radius=12,
        )
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<KeyRelease>", lambda e: self._validate())
        self._q_entries.append(entry)

    def _validate(self):
        name_ok = bool(self.name_entry.get().strip())
        q_ok    = any(e.get().strip() for e in self._q_entries)
        if name_ok and q_ok:
            self.start_btn.configure(
                state="normal", fg_color=T.BG_GREEN_DARK,
                hover_color=T.BG_GREEN_HOVER, text_color=T.GREEN_PRIMARY,
            )
        else:
            self.start_btn.configure(
                state="disabled", fg_color=T.BG_BUTTON,
                text_color=T.TEXT_DIM,
            )

    def _start(self):
        name      = self.name_entry.get().strip()
        questions = [e.get().strip() for e in self._q_entries if e.get().strip()]
        if not name or not questions:
            return
        session = create_session(name, questions)
        self._app.show_analysis(session)
