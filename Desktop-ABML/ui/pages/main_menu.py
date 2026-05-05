"""
ui/pages/main_menu.py — Pantalla 1: Menú principal (sidebar + panel derecho).
"""
import os

import customtkinter as ctk
from PIL import Image

import ui.theme as T
from ui.logo import make_brain_logo
from ui.assets import LOGO_FILE, BUTTON_FILE, HISTORIAL_FILE, CERRAR_FILE


class MainMenuPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=T.BG_MAIN, corner_radius=8)
        self._app = app
        self._build()

    # ── Construcción del layout ───────────────────────────────────────────────

    def _build(self):
        self.grid_columnconfigure(0, weight=0)  # sidebar fijo
        self.grid_columnconfigure(1, weight=0)  # separador fino
        self.grid_columnconfigure(2, weight=1)  # contenido derecho
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_separator()
        self._build_right_panel()

    def _build_sidebar(self):
        left = ctk.CTkFrame(self, fg_color=T.BG_DARK, corner_radius=0, width=310)
        left.grid(row=0, column=0, sticky="nsew")
        left.pack_propagate(False)
        left.grid_propagate(False)

        left.grid_rowconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=0)
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        content = ctk.CTkFrame(left, fg_color="transparent")
        content.grid(row=1, column=0, sticky="ew", padx=16)

        # Logo
        if os.path.exists(LOGO_FILE):
            logo_pil = Image.open(LOGO_FILE).convert("RGBA").resize((88, 88), Image.LANCZOS)
        else:
            logo_pil = make_brain_logo(88)
        self._logo_img = ctk.CTkImage(light_image=logo_pil, dark_image=logo_pil, size=(88, 88))
        ctk.CTkLabel(content, image=self._logo_img, text="").pack(pady=(0, 28))

        def _load_icon(path, hex_color, size=26):
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

        self._btn_img       = _load_icon(BUTTON_FILE,    T.GREEN_PRIMARY, size=28)
        self._historial_img = _load_icon(HISTORIAL_FILE, T.TEXT_LIGHT,   size=28)
        self._cerrar_img    = _load_icon(CERRAR_FILE,    T.RED_PRIMARY,  size=28)

        # Ítems del menú: (icon_img, title, subtitle, bg, hover_bg, color, icon_bg, hover_icon_bg, command)
        items = [
            (self._btn_img,       "Iniciar Analisis", "Captura y etiquetado",
             T.BG_GREEN_DIM, "#1f3a1f", T.GREEN_PRIMARY, T.BG_ICON_GREEN, "#2a4a2a", self._app.show_config),
            (self._historial_img, "Ver Historial",    "Analisis anteriores",
             T.BG_BUTTON,    "#2a2a2a", T.TEXT_LIGHT,   "#2e2e2e",        "#3a3a3a", self._app.show_history),
            (self._cerrar_img,    "Salir",            "Cerrar aplicacion",
             T.BG_RED_EXIT,  "#3d1010", T.RED_PRIMARY,  "#3a1010",        "#521818", self._app._on_close),
        ]

        for icon_img, title, sub, bg, hover_bg, col, icon_bg, hover_icon_bg, cmd in items:
            card = ctk.CTkFrame(content, fg_color=bg, corner_radius=T.CORNER_RADIUS_CARD, height=T.HEIGHT_CARD)
            card.pack_propagate(False)
            card.pack(fill="x", pady=5)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=14, pady=10)

            icon_box = ctk.CTkFrame(inner, fg_color=icon_bg, corner_radius=9, width=44, height=44)
            icon_box.pack_propagate(False)
            icon_box.pack(side="left")

            if icon_img is not None:
                ctk.CTkLabel(icon_box, image=icon_img, text="").pack(expand=True)

            txt = ctk.CTkFrame(inner, fg_color="transparent")
            txt.pack(side="left", padx=14)
            ctk.CTkLabel(txt, text=title, text_color=col,
                         font=T.bold(14), anchor="w").pack(anchor="w")
            ctk.CTkLabel(txt, text=sub,   text_color=T.TEXT_DIM,
                         font=T.font(11), anchor="w").pack(anchor="w")

            self._clickable(card, icon_box, bg, hover_bg, icon_bg, hover_icon_bg, cmd)

    def _build_separator(self):
        ctk.CTkFrame(self, fg_color=T.SEPARATOR, width=1, corner_radius=0
                     ).grid(row=0, column=1, sticky="nsew")

    def _build_right_panel(self):
        right = ctk.CTkFrame(self, fg_color=T.BG_MAIN, corner_radius=0)
        right.grid(row=0, column=2, sticky="nsew")
        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=0)
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        block = ctk.CTkFrame(right, fg_color="transparent")
        block.grid(row=1, column=0, sticky="ew", padx=44)

        # Sparkle + línea
        star_row = ctk.CTkFrame(block, fg_color="transparent")
        star_row.pack(fill="x", pady=(0, 18))
        ctk.CTkLabel(star_row, text="✦", text_color=T.GREEN_ACCENT,
                     font=T.font(18)).pack(side="left", padx=(0, 10))
        ctk.CTkFrame(star_row, fg_color=T.SEPARATOR, height=1).pack(side="left", fill="x", expand=True)

        # Título ABML — font compartido para poder reescalar en _on_resize
        tf = ctk.CTkFrame(block, fg_color="transparent")
        tf.pack(anchor="w")
        self._title_font = ctk.CTkFont(size=50, weight="bold")

        r1 = ctk.CTkFrame(tf, fg_color="transparent")
        r1.pack(anchor="w")
        for ch, rest, green in [("A", "plicacion ", True), ("B", "asada en", True)]:
            ctk.CTkLabel(r1, text=ch,   text_color=T.GREEN_PRIMARY if green else T.WHITE, font=self._title_font).pack(side="left")
            ctk.CTkLabel(r1, text=rest, text_color=T.WHITE,                               font=self._title_font).pack(side="left")

        r2 = ctk.CTkFrame(tf, fg_color="transparent")
        r2.pack(anchor="w")
        for ch, rest in [("M", "achine "), ("L", "earning")]:
            ctk.CTkLabel(r2, text=ch,   text_color=T.GREEN_PRIMARY, font=self._title_font).pack(side="left")
            ctk.CTkLabel(r2, text=rest, text_color=T.WHITE,         font=self._title_font).pack(side="left")

        self._app.bind("<Configure>", self._on_resize)

        # Subtítulo
        ctk.CTkLabel(block, text="para la  Deteccion de Patrones Conductuales",
                     text_color=T.TEXT_MID, font=T.font(17)).pack(anchor="w", pady=(10, 0))

        # Descripción
        bio_row = ctk.CTkFrame(block, fg_color="transparent")
        bio_row.pack(fill="x", pady=(6, 26))
        ctk.CTkLabel(bio_row, text="Utilizando ",      text_color=T.TEXT_DIM,     font=T.font(14)).pack(side="left")
        ctk.CTkLabel(bio_row, text="biometria facial", text_color=T.GREEN_PRIMARY, font=T.font(14)).pack(side="left")
        ctk.CTkLabel(bio_row, text=" computacional",   text_color=T.TEXT_DIM,     font=T.font(14)).pack(side="left")
        ctk.CTkLabel(bio_row, text="● ● ●",            text_color=T.GREEN_DOTS,   font=T.font(13)).pack(side="right")

        # Línea separadora + versión
        ctk.CTkFrame(block, fg_color=T.SEPARATOR, height=1).pack(fill="x")
        ver_row = ctk.CTkFrame(block, fg_color="transparent")
        ver_row.pack(anchor="w", pady=(10, 0))
        ctk.CTkLabel(ver_row, text="v1.0.0",                                  text_color=T.TEXT_MUTED, font=T.font(12)).pack(side="left")
        ctk.CTkLabel(ver_row, text="  •  Sistema de reconocimiento emocional", text_color=T.TEXT_MUTED, font=T.font(12)).pack(side="left")

    # ── Responsividad ─────────────────────────────────────────────────────────

    def _on_resize(self, event):
        if event.widget is not self._app:
            return
        # Escala proporcional: ventana base 1100 px → font 50
        new_size = max(30, min(90, int(50 * event.width / 1100)))
        self._title_font.configure(size=new_size)

    # ── Helpers de interactividad ─────────────────────────────────────────────

    def _clickable(self, card, icon_box, bg, hover_bg, icon_bg, hover_icon_bg, cmd):
        def on_click(e): cmd()
        def on_enter(e):
            card.configure(fg_color=hover_bg, cursor="hand2")
            icon_box.configure(fg_color=hover_icon_bg)
        def on_leave(e):
            card.configure(fg_color=bg, cursor="")
            icon_box.configure(fg_color=icon_bg)
        widget = card
        for w in self._all_children(widget) + [widget]:
            try:
                w.bind("<Button-1>", on_click)
                w.bind("<Enter>",    on_enter)
                w.bind("<Leave>",    on_leave)
            except Exception:
                pass

    def _all_children(self, w):
        ch = list(w.winfo_children())
        for c in list(ch):
            ch.extend(self._all_children(c))
        return ch
