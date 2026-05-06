"""
ui/tooltip.py — Tooltip con esquinas redondeadas acorde al tema oscuro de la app.
"""
import tkinter as tk
import customtkinter as ctk


# Color usado como clave de transparencia (debe ser único, no usado en la UI)
_TRANSP = "#000001"


class Tooltip:
    """Muestra un pequeño popup con esquinas redondeadas al pasar el cursor."""

    def __init__(self, widget, text: str, delay: int = 400):
        self._widget = widget
        self._text   = text
        self._delay  = delay
        self._tip    = None
        self._job    = None

        widget.bind("<Enter>",       self._schedule, add="+")
        widget.bind("<Leave>",       self._cancel,   add="+")
        widget.bind("<ButtonPress>", self._cancel,   add="+")

    def _schedule(self, _event=None):
        self._cancel()
        self._job = self._widget.after(self._delay, self._show)

    def _cancel(self, _event=None):
        if self._job:
            self._widget.after_cancel(self._job)
            self._job = None
        self._hide()

    def _show(self):
        w = self._widget
        x = w.winfo_rootx() + w.winfo_width() // 2
        y = w.winfo_rooty() + w.winfo_height() + 8

        self._tip = tk.Toplevel(w)
        self._tip.wm_overrideredirect(True)
        # El color de fondo del Toplevel actúa como clave de transparencia:
        # las esquinas del CTkFrame (que heredan este color) se vuelven invisibles.
        self._tip.configure(bg=_TRANSP)
        try:
            self._tip.wm_attributes("-transparentcolor", _TRANSP)
        except Exception:
            pass  # fallback: sin transparencia en corners, sigue funcional

        frame = ctk.CTkFrame(
            self._tip,
            fg_color="#1e1e1e",
            corner_radius=10,
            border_width=0,
        )
        frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text=self._text,
            text_color="#00e676",
            font=ctk.CTkFont(family="Segoe UI", size=9),
        ).pack(padx=10, pady=4)

        # Centrar horizontalmente sin salir de pantalla
        self._tip.update_idletasks()
        tip_w    = self._tip.winfo_width()
        screen_w = self._tip.winfo_screenwidth()
        x = max(4, min(x - tip_w // 2, screen_w - tip_w - 4))

        self._tip.wm_geometry(f"+{x}+{y}")
        self._tip.lift()

    def _hide(self):
        if self._tip:
            self._tip.destroy()
            self._tip = None
