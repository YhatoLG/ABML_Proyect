"""
ui/assets.py — Rutas centralizadas a todos los assets de la aplicación.

Las rutas se resuelven con resource_path() para que funcionen tanto en
desarrollo como empaquetadas con PyInstaller (sys._MEIPASS).

Estructura esperada de assets/:
    assets/
        logos/   imagen_2026-03-22_210857837.png
        icons/   imagen_2026-03-22_214416586.png
"""
import os
from utils import resource_path

LOGO_FILE           = resource_path(
    os.path.join("assets", "logos", "imagen_2026-03-22_210857837.png"))
APP_ICON_FILE       = resource_path(os.path.join("assets", "icons", "Logo_1.png"))
APP_ICO_FILE        = resource_path(os.path.join("assets", "icons", "Logo_1.ico"))
BUTTON_FILE         = resource_path(os.path.join("assets", "icons", "iniciar-sesion.png"))
HISTORIAL_FILE      = resource_path(os.path.join("assets", "icons", "historial.png"))
CERRAR_FILE         = resource_path(os.path.join("assets", "icons", "cerrar-sesion.png"))
FLECHA_IZQ_FILE     = resource_path(os.path.join("assets", "icons", "flecha-izquierda.png"))
USUARIO_FILE        = resource_path(os.path.join("assets", "icons", "usuario.png"))
REPORTE_FILE        = resource_path(os.path.join("assets", "icons", "reporte.png"))
DESCARGA_FILE       = resource_path(os.path.join("assets", "icons", "descarga-directa.png"))
ELIMINAR_FILE       = resource_path(os.path.join("assets", "icons", "eliminar-usuario.png"))
PERSONA_FILE        = resource_path(os.path.join("assets", "icons", "persona.png"))
PREGUNTA_FILE       = resource_path(os.path.join("assets", "icons", "Pregunta.png"))
MAS_FILE            = resource_path(os.path.join("assets", "icons", "mas.png"))
IMPORTAR_FILE       = resource_path(os.path.join("assets", "icons", "importar-archivo.png"))
EDITAR_FILE         = resource_path(os.path.join("assets", "icons", "editar-texto.png"))
LECHO_FILE          = resource_path(os.path.join("assets", "icons", "lecho.png"))
PLAY_FILE           = resource_path(os.path.join("assets", "icons", "jugar.png"))
DISQUETE_FILE          = resource_path(os.path.join("assets", "icons", "disquete.png"))
BORRAR_FILE            = resource_path(os.path.join("assets", "icons", "borrar.png"))
RECARGAR_FILE          = resource_path(os.path.join("assets", "icons", "recargar.png"))
CONTROLAR_FILE         = resource_path(os.path.join("assets", "icons", "controlar.png"))
FLECHA_CORRECTA_FILE   = resource_path(os.path.join("assets", "icons", "flecha-correcta.png"))
