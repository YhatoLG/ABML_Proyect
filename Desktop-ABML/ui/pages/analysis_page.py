"""
ui/pages/analysis_page.py — Pantalla 3: Análisis en tiempo real.

Separa captura (model/capture.py) y análisis de emoción
(model/emotion_analyzer.py) de la lógica de presentación.
"""
import os
import csv
import time
import random
import datetime
import threading

import cv2
import numpy as np
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk

import ui.theme as T
import ui.assets as A
from model.capture import get_sources, capture_frame
from model.emotion_analyzer import analyze_emotion
from model.session_manager import finish_session, create_session
from model.groups_manager import list_question_groups
from model.config import API_BASE_URL, API_SESSION, DATASET_DIR
from ui.pages.setup_page import _make_readonly


class AnalysisPage(ctk.CTkFrame):
    def __init__(self, master, app, session: dict, context: dict = None):
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=0)
        self._app     = app
        self.session  = session
        self.questions = session["questions"]

        # ── Contexto del grupo (para avance entre personas) ───────────────────
        ctx = context or {}
        self._person_group       : list = ctx.get("person_group", [])
        self._q_group_name       : str  = ctx.get("q_group_name", session.get("question_group", ""))
        self._n_questions        : int  = ctx.get("n_questions", len(self.questions))
        self._current_person_idx : int  = ctx.get("current_person_idx", 0)

        # Personas que ya completaron el análisis en este ciclo de grupo
        self._completed_persons   : set  = set(ctx.get("completed_persons", []))
        # Registros acumulados de todo el grupo (para el reporte final CSV)
        self._group_records       : list = list(ctx.get("group_records", []))
        # Bandera: bloquea nuevos saves mientras se carga la siguiente persona
        self._transitioning       : bool = False
        # Evita generar el reporte de grupo más de una vez
        self._group_report_saved  : bool = False

        # Estado de navegación de preguntas
        self.current_q_idx = 0
        self._saves_per_q: dict[int, int] = {}

        # Estado del frame capturado
        self.current_frame  = None
        self.display_frame  = None
        self._frame_res     = (0, 0)
        self._hwnd_cache: dict = {}

        # Estado de detección
        self.emotion       = "Neutral"
        self.emotion_prob  = 0.0
        self.status_text   = "Emoción: detectando..."
        self.is_running    = True

        # Contadores
        self.positive_count = 0
        self.negative_count = 0

        # Fuentes de captura
        self.capture_sources  = get_sources(app_title=self._app.title())
        self.selected_source  = ctk.StringVar(value=self.capture_sources[0])

        self._build()

        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        self._update_ui()
        self._notificar_pregunta_api()

    def stop(self):
        self.is_running = False

    # ── Construcción del layout ───────────────────────────────────────────────

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
        self._ic_recargar      = self._load_icon(A.RECARGAR_FILE,        "#000000",       18)
        self._ic_controlar     = self._load_icon(A.CONTROLAR_FILE,     T.GREEN_PRIMARY, 24)
        self._ic_controlar_opt = self._load_icon(A.CONTROLAR_FILE,     T.GREEN_PRIMARY, 12)
        self._ic_borrar_neg    = self._load_icon(A.BORRAR_FILE,        T.RED_PRIMARY,   24)
        self._ic_pregunta      = self._load_icon(A.PREGUNTA_FILE,      T.GREEN_PRIMARY, 12)
        self._ic_flecha_izq    = self._load_icon(A.FLECHA_IZQ_FILE,    T.GREEN_PRIMARY, 16)
        self._ic_flecha_der    = self._load_icon(A.FLECHA_CORRECTA_FILE, T.GREEN_PRIMARY, 16)
        self._ic_cerrar        = self._load_icon(A.CERRAR_FILE,        T.TEXT_MID,      18)
        self._ic_persona_sm    = self._load_icon(A.PERSONA_FILE,       T.GREEN_PRIMARY, 14)
        self._ic_persona_dim   = self._load_icon(A.PERSONA_FILE,       T.TEXT_DIM,      14)
        self._ic_pregunta_dim  = self._load_icon(A.PREGUNTA_FILE,      T.TEXT_DIM,      14)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_right_panel()

        # Atajos de teclado
        self._app.bind("<KeyPress-1>", lambda e: self._save(1))
        self._app.bind("<KeyPress-0>", lambda e: self._save(0))
        self._app.bind("<Escape>",     lambda e: self._exit())

    def _build_left_panel(self):
        left = ctk.CTkFrame(self, fg_color=T.BG_DARK, corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        # Barra superior: selector de fuente
        top_bar = ctk.CTkFrame(left, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))

        ctk.CTkLabel(top_bar, text="Capturar desde:", text_color=T.TEXT_MID,
                     font=T.font(13)).pack(side="left", padx=(0, 6))

        self.combo_source = ctk.CTkComboBox(
            top_bar, values=self.capture_sources, variable=self.selected_source,
            width=290, fg_color="#1c1c1c", border_color="#333333",
            button_color="#333333", dropdown_fg_color="#1c1c1c", text_color="#dddddd",
        )
        self.combo_source.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            top_bar, image=self._ic_recargar, text="  Actualizar",
            command=self._refresh_sources,
            width=140, height=34, fg_color=T.GREEN_BRIGHT, hover_color="#00a844",
            text_color="#000000", font=T.bold(13), corner_radius=17,
        ).pack(side="left")

        # Canvas de video
        self.video_canvas = tk.Canvas(left, bg=T.BG_MAIN, highlightthickness=0)
        self.video_canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=4)

        # Etiqueta de estado
        self.status_label = ctk.CTkLabel(left, text=self.status_text,
                                          font=T.font(13), text_color=T.TEXT_LIGHT)
        self.status_label.grid(row=2, column=0, pady=(2, 10))

    def _build_right_panel(self):
        right = ctk.CTkFrame(self, fg_color=T.BG_DARK, corner_radius=12, width=400)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right.pack_propagate(False)
        right.grid_propagate(False)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(3, weight=1)   # question card expands

        # ── Row 0: Selectores compactos ───────────────────────────────────────
        self._build_selector_card(right)

        # ── Row 1: Verdad (1) y Falso (0) lado a lado ────────────────────────
        tf = ctk.CTkFrame(right, fg_color="transparent")
        tf.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        tf.grid_columnconfigure(0, weight=1)
        tf.grid_columnconfigure(1, weight=1)

        # — Verdad (1) —
        pos_card = ctk.CTkFrame(tf, fg_color=T.BG_POS_CARD, corner_radius=10, height=74)
        pos_card.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        pos_card.pack_propagate(False)

        pos_top = ctk.CTkFrame(pos_card, fg_color="transparent")
        pos_top.pack(side="top", fill="x", padx=6, pady=(4, 0))
        self.pos_badge = ctk.CTkLabel(
            pos_top, text="0", text_color=T.WHITE, font=T.bold(12),
            fg_color=T.GREEN_LIVE, corner_radius=10, width=22, height=22,
        )
        self.pos_badge.pack(side="right")

        pos_mid = ctk.CTkFrame(pos_card, fg_color="transparent")
        pos_mid.pack(expand=True, fill="both")
        pos_cnt = ctk.CTkFrame(pos_mid, fg_color="transparent")
        pos_cnt.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(pos_cnt, image=self._ic_controlar, text="").pack(side="left")
        ctk.CTkLabel(pos_cnt, text="  Verdad  (1)", text_color=T.GREEN_PRIMARY, font=T.bold(12)).pack(side="left")
        self._bind_card(pos_card, lambda: self._save(1))

        # — Falso (0) —
        neg_card = ctk.CTkFrame(tf, fg_color=T.BG_RED_DIM, corner_radius=10, height=74)
        neg_card.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        neg_card.pack_propagate(False)

        neg_top = ctk.CTkFrame(neg_card, fg_color="transparent")
        neg_top.pack(side="top", fill="x", padx=6, pady=(4, 0))
        self.neg_badge = ctk.CTkLabel(
            neg_top, text="0", text_color=T.WHITE, font=T.bold(12),
            fg_color=T.RED_DARK, corner_radius=10, width=22, height=22,
        )
        self.neg_badge.pack(side="right")

        neg_mid = ctk.CTkFrame(neg_card, fg_color="transparent")
        neg_mid.pack(expand=True, fill="both")
        neg_cnt = ctk.CTkFrame(neg_mid, fg_color="transparent")
        neg_cnt.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(neg_cnt, image=self._ic_borrar_neg, text="").pack(side="left")
        ctk.CTkLabel(neg_cnt, text="  Falso  (0)", text_color=T.RED_PRIMARY, font=T.bold(12)).pack(side="left")
        self._bind_card(neg_card, lambda: self._save(0))

        # ── Row 2: Emoción detectada (compacta) ───────────────────────────────
        emo_card = ctk.CTkFrame(right, fg_color=T.BG_CARD, corner_radius=10)
        emo_card.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 6))

        emo_inner = ctk.CTkFrame(emo_card, fg_color="transparent")
        emo_inner.pack(fill="x", padx=12, pady=(8, 4))
        emo_inner.grid_columnconfigure(0, weight=1)
        emo_inner.grid_columnconfigure(1, weight=0)

        emo_left = ctk.CTkFrame(emo_inner, fg_color="transparent")
        emo_left.grid(row=0, column=0, sticky="w")
        emo_hdr = ctk.CTkFrame(emo_left, fg_color="transparent")
        emo_hdr.pack(anchor="w")
        ctk.CTkLabel(emo_hdr, text="⬤ ", text_color=T.GREEN_PRIMARY, font=T.font(8)).pack(side="left")
        ctk.CTkLabel(emo_hdr, text="ANALIZANDO", text_color=T.GREEN_PRIMARY, font=T.bold(9)).pack(side="left")
        self.emotion_big = ctk.CTkLabel(emo_left, text="Neutral", text_color=T.WHITE, font=T.bold(22))
        self.emotion_big.pack(anchor="w")

        emo_right = ctk.CTkFrame(emo_inner, fg_color="transparent")
        emo_right.grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(emo_right, text="Confianza", text_color=T.TEXT_DIM, font=T.font(10)).pack(anchor="e")
        self.conf_pct = ctk.CTkLabel(emo_right, text="0.00%", text_color=T.GREEN_PRIMARY, font=T.bold(14))
        self.conf_pct.pack(anchor="e")

        self.conf_bar = ctk.CTkProgressBar(
            emo_card, fg_color=T.BG_HOVER, progress_color=T.GREEN_PRIMARY, height=6, corner_radius=3)
        self.conf_bar.set(0)
        self.conf_bar.pack(fill="x", padx=12, pady=(2, 8))

        # ── Row 3: Tarjeta de pregunta + opciones (expande) ───────────────────
        q_card = ctk.CTkFrame(right, fg_color=T.BG_GREEN_Q, corner_radius=10)
        q_card.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 6))
        q_card.grid_columnconfigure(0, weight=1)
        q_card.grid_rowconfigure(2, weight=1)  # opciones expanden

        # Header con contador
        qh = ctk.CTkFrame(q_card, fg_color="transparent")
        qh.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        ctk.CTkLabel(qh, image=self._ic_pregunta, text="").pack(side="left", padx=(0, 4))
        ctk.CTkLabel(qh, text="PREGUNTA ACTUAL",
                     text_color=T.GREEN_PRIMARY, font=T.bold(10)).pack(side="left")
        self.q_count_lbl = ctk.CTkLabel(qh, text="1 / 1", text_color=T.GREEN_PRIMARY, font=T.bold(10))
        self.q_count_lbl.pack(side="right")

        # Texto de la pregunta
        first_q    = self.questions[0] if self.questions else ""
        first_text = first_q["text"] if isinstance(first_q, dict) else first_q
        self.q_text_lbl = ctk.CTkLabel(
            q_card, text=first_text,
            text_color=T.WHITE, font=T.bold(13),
            wraplength=320, justify="left", anchor="w",
        )
        self.q_text_lbl.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))

        # Opciones de respuesta (scrollable, expande verticalmente)
        self._q_opts_frame = ctk.CTkFrame(
            q_card, fg_color="transparent", corner_radius=0)
        self._q_opts_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 4))
        self._render_opts(first_q)

        # Persona + progreso
        bot = ctk.CTkFrame(q_card, fg_color="transparent")
        bot.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 4))
        ctk.CTkLabel(bot, image=self._ic_persona_sm, text="").pack(side="left", padx=(0, 6))
        self.person_name_lbl = ctk.CTkLabel(
            bot, text=self.session['name'],
            text_color=T.GREEN_PRIMARY, font=T.bold(11), anchor="w",
        )
        self.person_name_lbl.pack(side="left")
        self.q_prog_lbl = ctk.CTkLabel(bot, text="0%", text_color=T.TEXT_MID, font=T.font(10))
        self.q_prog_lbl.pack(side="right")

        # Navegación
        nav = ctk.CTkFrame(q_card, fg_color="transparent")
        nav.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 10))
        ctk.CTkButton(
            nav, image=self._ic_flecha_izq, text="  Anterior", width=110, height=30,
            fg_color=T.BG_ICON_GREEN, hover_color="#243a24",
            text_color=T.GREEN_PRIMARY, font=T.font(11),
            corner_radius=8, command=self._prev_q,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            nav, image=self._ic_flecha_der, text="  Siguiente", width=110, height=30,
            fg_color=T.BG_ICON_GREEN, hover_color="#243a24",
            text_color=T.GREEN_PRIMARY, font=T.font(11),
            corner_radius=8, command=self._next_q,
        ).pack(side="left")

        # ── Row 4: Salir ──────────────────────────────────────────────────────
        ctk.CTkButton(
            right, image=self._ic_cerrar, text="  Salir  (ESC)",
            command=self._exit,
            fg_color=T.BG_BUTTON, hover_color=T.BG_HOVER,
            text_color=T.TEXT_MID, font=T.font(12),
            corner_radius=T.CORNER_RADIUS_BTN, height=40,
        ).grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 12))

    # ── Selectores compactos (banco / persona / N) ────────────────────────────

    def _build_selector_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=T.BG_CARD, corner_radius=10)
        card.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=(8, 8))

        # — Banco de preguntas —
        r_bank = ctk.CTkFrame(inner, fg_color="transparent")
        r_bank.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(r_bank, image=self._ic_pregunta_dim, text="", width=20).pack(side="left", padx=(0, 4))

        q_groups = list_question_groups()
        q_names  = [g["name"] for g in q_groups]
        self._sel_q_var = ctk.StringVar(
            value=self._q_group_name if self._q_group_name in q_names
            else (q_names[0] if q_names else ""))
        self._sel_q_combo = ctk.CTkComboBox(
            r_bank, variable=self._sel_q_var,
            values=q_names if q_names else [""],
            height=30, fg_color=T.BG_DARK, border_color=T.BG_BUTTON,
            button_color=T.BG_HOVER, dropdown_fg_color=T.BG_CARD,
            text_color=T.TEXT_LIGHT, font=T.font(11),
            corner_radius=6, command=self._on_sel_q_group_change,
        )
        self._sel_q_combo.pack(side="left", fill="x", expand=True)
        _make_readonly(self._sel_q_combo)

        # — Persona: solo muestra las que aún no completaron —
        r_person = ctk.CTkFrame(inner, fg_color="transparent")
        r_person.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(r_person, image=self._ic_persona_dim, text="", width=20).pack(side="left", padx=(0, 4))

        people   = [p for p in self._person_group if p not in self._completed_persons]
        cur_name = self.session["name"]
        self._sel_person_var = ctk.StringVar(
            value=cur_name if cur_name in people else (people[0] if people else ""))
        self._sel_person_combo = ctk.CTkComboBox(
            r_person, variable=self._sel_person_var,
            values=people if people else [cur_name],
            height=30, fg_color=T.BG_DARK, border_color=T.BG_BUTTON,
            button_color=T.BG_HOVER, dropdown_fg_color=T.BG_CARD,
            text_color=T.TEXT_LIGHT, font=T.font(11),
            corner_radius=6, command=self._on_sel_person_change,
        )
        self._sel_person_combo.pack(side="left", fill="x", expand=True)
        _make_readonly(self._sel_person_combo)

        # — Nº de preguntas —
        r_n = ctk.CTkFrame(inner, fg_color="transparent")
        r_n.pack(fill="x")
        ctk.CTkLabel(r_n, text="Nº preguntas:", font=T.font(11), text_color=T.TEXT_DIM).pack(side="left", padx=(24, 8))

        self._sel_n = self._n_questions
        ctk.CTkButton(
            r_n, text="−", width=30, height=28,
            fg_color=T.BG_BUTTON, hover_color=T.BG_HOVER, corner_radius=6,
            text_color=T.WHITE, font=T.bold(16),
            command=lambda: self._change_sel_n(-1),
        ).pack(side="left")
        self._sel_n_lbl = ctk.CTkLabel(
            r_n, text=str(self._sel_n),
            fg_color=T.BG_DARK, corner_radius=6,
            text_color=T.WHITE, font=T.bold(14), width=36, height=28,
        )
        self._sel_n_lbl.pack(side="left", padx=4)
        ctk.CTkButton(
            r_n, text="+", width=30, height=28,
            fg_color=T.BG_BUTTON, hover_color=T.BG_HOVER, corner_radius=6,
            text_color=T.WHITE, font=T.bold(16),
            command=lambda: self._change_sel_n(1),
        ).pack(side="left")

    # ── Lógica de selectores ──────────────────────────────────────────────────

    def _on_sel_q_group_change(self, value: str):
        """Cambiar banco recarga las preguntas para la persona actual.
        Las personas ya completadas siguen bloqueadas aunque cambie el grupo."""
        if value == self._q_group_name:
            return
        self._q_group_name = value
        self._update_person_selector()
        self._load_new_person(self.session["name"])

    def _on_sel_person_change(self, value: str):
        """Cambiar persona manualmente carga una nueva sesión para esa persona."""
        if value == self.session["name"]:
            return
        if value in self._completed_persons:
            # Persona ya evaluada — revertir selección al sujeto actual
            self._sel_person_var.set(self.session["name"])
            return
        if value in self._person_group:
            self._current_person_idx = self._person_group.index(value)
        self._load_new_person(value)

    def _update_person_selector(self):
        """Refresca el combo de personas eliminando a quienes ya completaron."""
        available = [p for p in self._person_group if p not in self._completed_persons]
        self._sel_person_combo.configure(values=available if available else [""])

    def _change_sel_n(self, delta: int):
        self._sel_n = max(1, self._sel_n + delta)
        self._n_questions = self._sel_n
        self._sel_n_lbl.configure(text=str(self._sel_n))

    # ── Navegación de preguntas ───────────────────────────────────────────────

    def _prev_q(self):
        if self.current_q_idx > 0:
            self.current_q_idx -= 1
            self._refresh_q_display()
            self._notificar_pregunta_api()

    def _next_q(self):
        if self.current_q_idx < len(self.questions) - 1:
            self.current_q_idx += 1
            self._refresh_q_display()
            self._notificar_pregunta_api()

    def _notificar_pregunta_api(self):
        """Envía la pregunta actual al servidor para que la retransmita vía SignalR."""
        def _post():
            if not self.questions:
                return
            q = self.questions[self.current_q_idx]
            texto    = q["text"]           if isinstance(q, dict) else q
            opciones = q.get("options", []) if isinstance(q, dict) else []
            correcto = q.get("correct", -1) if isinstance(q, dict) else -1
            try:
                API_SESSION.post(
                    f"{API_BASE_URL}/api/preguntas/siguiente",
                    json={
                        "id":                self.current_q_idx,
                        "texto":             texto,
                        "opciones":          [str(o) for o in opciones],
                        "respuestaCorrecta": correcto,
                        "grupoNombre":       self._q_group_name or "",
                    },
                    timeout=5,
                )
            except Exception:
                pass

        threading.Thread(target=_post, daemon=True).start()

    def _notificar_fin_api(self):
        """Señaliza fin de análisis a la web (id=-1 actúa como centinela)."""
        def _post():
            try:
                API_SESSION.post(
                    f"{API_BASE_URL}/api/preguntas/siguiente",
                    json={"id": -1, "texto": "", "opciones": [], "respuestaCorrecta": -1, "grupoNombre": ""},
                    timeout=5,
                )
            except Exception:
                pass

        threading.Thread(target=_post, daemon=True).start()

    def _refresh_q_display(self):
        n     = len(self.questions)
        i     = self.current_q_idx
        q     = self.questions[i] if n > 0 else ""
        text  = q["text"] if isinstance(q, dict) else q
        saves = self._saves_per_q.get(i, 0)
        total = self.positive_count + self.negative_count
        pct   = int(saves / total * 100) if total > 0 else 0
        self.q_count_lbl.configure(text=f"{i + 1} / {n}")
        self.q_text_lbl.configure(text=text)
        self.q_prog_lbl.configure(text=f"{pct}%")
        self._render_opts(q)

    def _render_opts(self, q):
        """Actualiza el panel de opciones de la pregunta actual."""
        for w in self._q_opts_frame.winfo_children():
            w.destroy()
        if not isinstance(q, dict):
            return
        options     = q.get("options", [])
        correct_idx = q.get("correct", -1)
        if not options:
            return
        letters = "ABCDEFGHIJKLMNOP"
        for j, opt in enumerate(options):
            letter     = letters[j] if j < len(letters) else str(j + 1)
            is_correct = (j == correct_idx)
            color      = T.GREEN_PRIMARY if is_correct else T.TEXT_DIM

            row = ctk.CTkFrame(self._q_opts_frame, fg_color="transparent")
            row.pack(anchor="w", pady=1, fill="x")

            if is_correct and self._ic_controlar_opt:
                ctk.CTkLabel(row, image=self._ic_controlar_opt, text="").pack(
                    side="left", padx=(0, 4))
            else:
                ctk.CTkLabel(row, text="·", text_color=color,
                             font=T.font(11), width=14).pack(side="left")

            ctk.CTkLabel(
                row,
                text=f"{letter}. {opt}",
                text_color=color,
                font=T.bold(11) if is_correct else T.font(11),
                anchor="w", wraplength=285, justify="left",
            ).pack(side="left", fill="x", expand=True)

    # ── Guardar registro ──────────────────────────────────────────────────────

    def _save(self, response: int):
        if self.current_frame is None or self._transitioning:
            return

        timestamp  = datetime.datetime.now().isoformat()
        image_name = timestamp.replace(":", "-") + ".png"
        images_dir = os.path.join(self.session["dir"], "images")
        image_path = os.path.join(images_dir, image_name)
        cv2.imwrite(image_path, self.current_frame)

        q             = self.questions[self.current_q_idx] if self.questions else ""
        question_text = q["text"] if isinstance(q, dict) else q

        correct_answer = ""
        if response == 1 and isinstance(q, dict):
            opts    = q.get("options", [])
            cor_idx = q.get("correct", -1)
            if 0 <= cor_idx < len(opts):
                correct_answer = opts[cor_idx]

        # Acumular en el reporte del grupo
        self._group_records.append({
            "persona":            self.session["name"],
            "pregunta":           question_text,
            "respuesta_correcta": correct_answer,
            "emocion":            self.emotion,
            "prob_emocion":       round(self.emotion_prob, 2),
            "respondio":          response == 1,
            "timestamp":          timestamp,
        })

        def _post_registro():
            try:
                API_SESSION.post(f"{API_BASE_URL}/api/registros", json={
                    "sesion_id":          self.session["id"],
                    "timestamp":          timestamp,
                    "pregunta":           question_text,
                    "respuesta_correcta": correct_answer,
                    "emocion":            self.emotion,
                    "prob_emocion":       round(self.emotion_prob, 2),
                    "respondio":          response == 1,
                    "imagen_path":        image_path,
                }, timeout=5)
            except Exception:
                pass
        threading.Thread(target=_post_registro, daemon=True).start()

        if response == 1:
            self.positive_count += 1
        else:
            self.negative_count += 1

        self._saves_per_q[self.current_q_idx] = self._saves_per_q.get(self.current_q_idx, 0) + 1
        self._refresh_q_display()

        label = "Positivo" if response == 1 else "Negativo"
        self.status_label.configure(text=f"¡Guardado! ({label})", text_color=T.BLUE_INFO)

        # Avance de preguntas / personas
        at_last = (self.current_q_idx >= len(self.questions) - 1)
        if not at_last:
            self.after(100, self._next_q)
        elif self._person_group:
            # Última pregunta → marcar persona como completada y avanzar de inmediato
            self._trigger_person_completed()
        else:
            self.after(1500, lambda: self.status_label.configure(text_color=T.TEXT_LIGHT))

    # ── Avance automático entre personas ─────────────────────────────────────

    def _trigger_person_completed(self):
        if self._transitioning:
            return
        self._transitioning = True
        name = self.session["name"]
        # Registrar persona como completada y actualizar selector
        self._completed_persons.add(name)
        self._update_person_selector()
        self.status_label.configure(
            text=f"✓  {name} completó · Cargando siguiente...",
            text_color=T.GREEN_PRIMARY,
        )
        self.after(400, self._advance_to_next_person)

    def _advance_to_next_person(self):
        # Buscar el siguiente índice cuya persona aún no haya completado
        next_idx = self._current_person_idx + 1
        while next_idx < len(self._person_group):
            if self._person_group[next_idx] not in self._completed_persons:
                break
            next_idx += 1

        if next_idx >= len(self._person_group):
            # Todas las personas terminaron → generar archivo de grupo
            self._export_group_report()
            self._notificar_fin_api()
            self.status_label.configure(
                text="✓  Todos completaron la prueba · Cerrando sesión...",
                text_color=T.GREEN_PRIMARY,
            )
            self.after(2200, self._exit)
            return

        self._current_person_idx = next_idx
        next_person = self._person_group[next_idx]
        self._load_new_person(next_person)

    def _export_group_report(self):
        """Genera un CSV único con los registros de todas las personas del grupo."""
        if not self._group_records or self._group_report_saved:
            return
        self._group_report_saved = True
        now        = datetime.datetime.now()
        date_str   = now.strftime("%Y-%m-%d_%H-%M-%S")
        group_safe = "".join(
            c if c.isalnum() or c in "-_ " else "_"
            for c in (self._q_group_name or "grupo")
        )
        filename = f"grupo_{group_safe}_{date_str}.csv"
        out_dir  = os.path.join(DATASET_DIR, "grupos")
        os.makedirs(out_dir, exist_ok=True)
        filepath = os.path.join(out_dir, filename)

        fields = ["persona", "pregunta", "respuesta_correcta",
                  "emocion", "prob_emocion", "respondio", "timestamp"]
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for rec in self._group_records:
                writer.writerow({k: rec.get(k, "") for k in fields})

    def _load_new_person(self, person_name: str):
        """Finaliza la sesión actual y crea una nueva para la persona indicada.
        La consulta al API se hace en un thread para no bloquear la UI."""
        finish_session(self.session["id"])
        self.status_label.configure(
            text=f"⏳  Preparando preguntas para {person_name}...",
            text_color=T.TEXT_MID,
        )

        n_questions = self._n_questions
        q_group     = self._q_group_name

        def _prepare():
            groups = list_question_groups()
            g      = next((gr for gr in groups if gr["name"] == q_group), None)
            if not g:
                self.after(0, self._exit)
                return
            all_qs      = g["questions"]
            n           = min(n_questions, len(all_qs))
            selected    = random.sample(all_qs, n)
            new_session = create_session(person_name, selected, question_group=q_group)
            self.after(0, lambda: self._apply_new_person(person_name, n, selected, new_session))

        threading.Thread(target=_prepare, daemon=True).start()

    def _apply_new_person(self, person_name: str, n: int, selected: list, new_session: dict):
        """Aplica el estado de la nueva persona en el hilo principal de la UI."""
        self.session        = new_session
        self.questions      = selected
        self.current_q_idx  = 0
        self._saves_per_q   = {}
        self.positive_count = 0
        self.negative_count = 0

        self._sel_person_var.set(person_name)
        self.person_name_lbl.configure(text=person_name)
        self.pos_badge.configure(text="0")
        self.neg_badge.configure(text="0")
        self._refresh_q_display()
        self._notificar_pregunta_api()
        self.status_label.configure(
            text=f"👤  {person_name}  ·  {n} preguntas  ·  Análisis Activo",
            text_color=T.GREEN_PRIMARY,
        )
        # Habilitar saves nuevamente ahora que la persona está lista
        self._transitioning = False

    # ── Salir ─────────────────────────────────────────────────────────────────

    def _exit(self):
        self._cleanup_on_close()
        for key in ("<KeyPress-1>", "<KeyPress-0>", "<Escape>"):
            try:
                self._app.unbind(key)
            except Exception:
                pass
        self._app.show_main_menu()

    def _cleanup_on_close(self):
        """Limpieza al cerrar (ESC, botón Salir o X de Windows) — sin navegar."""
        self._export_group_report()
        self._notificar_fin_api()
        finish_session(self.session["id"])
        self.stop()

    # ── Fuentes de captura ────────────────────────────────────────────────────

    def _refresh_sources(self):
        self._hwnd_cache.clear()
        self.capture_sources = get_sources(app_title=self._app.title())
        self.combo_source.configure(values=self.capture_sources)
        if self.selected_source.get() not in self.capture_sources:
            self.selected_source.set(self.capture_sources[0])

    # ── Loop de captura (hilo secundario) ─────────────────────────────────────

    def _capture_loop(self):
        last_analysis = 0.0
        error_msg     = ""

        while self.is_running:
            source = self.selected_source.get()
            try:
                frame, err = capture_frame(source, self._hwnd_cache)

                if frame is not None and frame.size > 0:
                    h0, w0 = frame.shape[:2]
                    self.current_frame = frame
                    self._frame_res    = (w0, h0)
                    self.display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    if time.time() - last_analysis > 0.5:  # ANALYSIS_INTERVAL
                        try:
                            self.emotion, self.emotion_prob = analyze_emotion(frame)
                            error_msg = ""
                        except Exception as exc:
                            error_msg = str(exc).split("\n")[0][:50]
                        last_analysis = time.time()

                    self.status_text = (
                        f"Emoción: {self.emotion} ({self.emotion_prob:.2f}%) | "
                        + (error_msg if error_msg else "Análisis Activo")
                    )
                elif err:
                    error_msg = err

            except Exception as exc:
                print("Error captura:", exc)
                time.sleep(1)

            time.sleep(0.01)

    # ── Loop de actualización UI (hilo principal) ─────────────────────────────

    def _update_ui(self):
        canvas = self.video_canvas
        cw, ch = canvas.winfo_width(), canvas.winfo_height()

        if self.display_frame is not None and cw > 1 and ch > 1:
            img      = Image.fromarray(self.display_frame)
            iw, ih   = img.size
            scale    = min(cw / iw, ch / ih)
            nw, nh   = int(iw * scale), int(ih * scale)
            img      = img.resize((nw, nh), Image.LANCZOS)
            x0, y0   = (cw - nw) // 2, (ch - nh) // 2
            x1, y1   = x0 + nw, y0 + nh

            canvas.delete("all")
            tk_img          = ImageTk.PhotoImage(image=img)
            canvas._tk_img  = tk_img   # mantener referencia
            canvas.create_image(x0, y0, anchor="nw", image=tk_img)
            self._draw_corners(canvas, x0, y0, x1, y1)

            if self._frame_res[0] > 0:
                canvas.create_text(
                    x0 + 8, y1 - 6,
                    text=f"{self._frame_res[0]}×{self._frame_res[1]}",
                    fill=T.WHITE, anchor="sw", font=("Arial", 10),
                )

        self.status_label.configure(text=self.status_text)
        self.emotion_big.configure(text=self.emotion.capitalize())
        self.conf_pct.configure(text=f"{self.emotion_prob:.2f}%")
        self.conf_bar.set(min(self.emotion_prob / 100.0, 1.0))
        self.pos_badge.configure(text=str(self.positive_count))
        self.neg_badge.configure(text=str(self.negative_count))

        if self.is_running:
            self.after(30, self._update_ui)

    def _draw_corners(self, canvas, x0, y0, x1, y1, size=20, lw=2):
        c = T.GREEN_CORNER
        canvas.create_line(x0,        y0 + size, x0,  y0,  x0 + size, y0,  fill=c, width=lw)
        canvas.create_line(x1 - size, y0,        x1,  y0,  x1,        y0 + size, fill=c, width=lw)
        canvas.create_line(x0,        y1 - size, x0,  y1,  x0 + size, y1,  fill=c, width=lw)
        canvas.create_line(x1 - size, y1,        x1,  y1,  x1,        y1 - size, fill=c, width=lw)

    def _bind_card(self, widget, cmd):
        try:
            widget.bind("<Button-1>", lambda e: cmd())
            widget.bind("<Enter>",    lambda e: widget.configure(cursor="hand2"))
            widget.bind("<Leave>",    lambda e: widget.configure(cursor=""))
        except Exception:
            pass
        for child in widget.winfo_children():
            self._bind_card(child, cmd)
