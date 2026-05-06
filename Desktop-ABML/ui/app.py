"""
ui/app.py — Controlador principal de ventanas (navegación entre páginas).
"""
import os
import customtkinter as ctk
import ui.theme as T


class App(ctk.CTk):
    """
    Ventana raíz de la aplicación.
    Gestiona la navegación entre páginas reemplazando el contenido
    del frame contenedor (_wrap) sin cerrar la ventana.
    """

    def __init__(self):
        super().__init__()
        self.title("ABML — Deteccion de Patrones Conductuales")
        self.geometry("1100x650")
        self.minsize(900, 550)
        self.configure(fg_color=T.BG_MAIN)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._set_icon()

        # Marco con borde verde que envuelve todo el contenido
        self._wrap = ctk.CTkFrame(
            self,
            fg_color=T.BG_MAIN,
            border_color=T.BORDER_GREEN,
            border_width=1,
            corner_radius=10,
        )
        self._wrap.pack(fill="both", expand=True, padx=4, pady=4)

        self._page = None
        self.show_main_menu()

    def _set_icon(self):
        from ui.assets import APP_ICO_FILE
        if not os.path.exists(APP_ICO_FILE):
            return
        try:
            self.iconbitmap(default=APP_ICO_FILE)
        except Exception:
            pass

    # ── Navegación ────────────────────────────────────────────────────────────

    def _clear(self):
        """Destruye la página actual llamando a stop() si la tiene."""
        if self._page:
            if hasattr(self._page, "stop"):
                self._page.stop()
            self._page.destroy()
            self._page = None

    def show_main_menu(self):
        from ui.pages.main_menu import MainMenuPage
        self._clear()
        self._page = MainMenuPage(self._wrap, self)
        self._page.pack(fill="both", expand=True)

    def show_config(self):
        from ui.pages.setup_page import SetupPage
        self._clear()
        self._page = SetupPage(self._wrap, self)
        self._page.pack(fill="both", expand=True)

    def show_analysis(self, session: dict, context: dict = None):
        from ui.pages.analysis_page import AnalysisPage
        self._clear()
        self._page = AnalysisPage(self._wrap, self, session, context)
        self._page.pack(fill="both", expand=True)

    def show_history(self):
        from ui.pages.history_page import HistoryPage
        self._clear()
        self._page = HistoryPage(self._wrap, self)
        self._page.pack(fill="both", expand=True)

    def _on_close(self):
        self._clear()
        self.destroy()
