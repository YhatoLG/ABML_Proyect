"""
utils.py — Utilidades compartidas entre capas.
"""
import os
import sys


def resource_path(relative_path: str) -> str:
    """
    Devuelve la ruta absoluta a un recurso.
    - En desarrollo: relativa a la raíz del proyecto (donde está main.py).
    - En PyInstaller (frozen): relativa a sys._MEIPASS (carpeta temporal del bundle).
    """
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


def data_path(relative_path: str) -> str:
    """
    Devuelve la ruta absoluta a datos de usuario (dataset, sesiones, etc.).
    Siempre apunta a la carpeta del ejecutable / raíz del proyecto,
    NUNCA a sys._MEIPASS (que es de solo lectura en el .exe empaquetado).
    """
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)
