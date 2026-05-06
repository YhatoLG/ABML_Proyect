"""
main.py — Punto de entrada de la aplicación ABML.

Ejecutar en desarrollo:
    python main.py

Empaquetar con PyInstaller:
    pyinstaller abml.spec
"""

import customtkinter as ctk
from ui.app import App


def main():
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
