"""
ui/theme.py — Paleta de colores, tipografía y helpers de estilo centralizados.

Importar con:
    import ui.theme as T

    btn = ctk.CTkButton(..., fg_color=T.BG_GREEN_DIM, text_color=T.GREEN_PRIMARY, font=T.bold(14))
"""
import customtkinter as ctk

# ── Fondos ────────────────────────────────────────────────────────────────────
BG_MAIN        = "#0a0a0a"   # fondo principal de la ventana
BG_DARK        = "#111111"   # sidebar / paneles laterales
BG_PANEL       = "#0d0d0d"   # fondo de páginas de análisis
BG_CARD        = "#1a1a1a"   # tarjetas internas (emotion card)
BG_BUTTON      = "#1e1e1e"   # botones desactivados / neutrales
BG_HOVER       = "#2a2a2a"   # hover de botones neutrales

# ── Bordes ────────────────────────────────────────────────────────────────────
BORDER_GREEN   = "#1e4d1e"   # borde exterior de la ventana
SEPARATOR      = "#1e1e1e"   # líneas separadoras

# ── Verdes ────────────────────────────────────────────────────────────────────
GREEN_PRIMARY  = "#00e676"   # verde principal (títulos, badges, labels activos)
GREEN_BRIGHT   = "#00c853"   # botón "Actualizar"
GREEN_CORNER   = "#00ff41"   # esquinas del canvas de video
GREEN_LIVE     = "#00a845"   # badge de conteo positivo
GREEN_DOT      = "#00ff41"   # punto de status en logo

BG_GREEN_DIM   = "#162316"   # fondo de tarjeta "Iniciar Análisis"
BG_GREEN_DARK  = "#162016"   # botón habilitado (start)
BG_GREEN_HOVER = "#1f3a1f"   # hover de botón habilitado
BG_GREEN_Q     = "#0d1f0d"   # fondo de tarjeta de pregunta
BG_POS_CARD    = "#003d1a"   # tarjeta "Guardar Positivo"
BG_ICON_GREEN  = "#1a2e1a"   # fondo de íconos verdes
LOGO_BG        = "#1a2e1a"   # fondo redondeado del logo cerebro

# ── Rojos ─────────────────────────────────────────────────────────────────────
RED_PRIMARY    = "#ff5252"   # texto / íconos de peligro
RED_DARK       = "#b71c1c"   # badge de conteo negativo
BG_RED_DIM     = "#3d0007"   # tarjeta "Guardar Negativo"
BG_RED_EXIT    = "#280808"   # tarjeta "Salir"

# ── Texto ─────────────────────────────────────────────────────────────────────
WHITE          = "#ffffff"
TEXT_LIGHT     = "#cccccc"   # texto general claro
TEXT_MID       = "#888888"   # texto secundario
TEXT_DIM       = "#555555"   # texto apagado / subtítulos
TEXT_DARKER    = "#444444"   # hints / placeholders
TEXT_MUTED     = "#3a3a3a"   # versión / metadatos

# ── Especiales ────────────────────────────────────────────────────────────────
BLUE_INFO      = "#17a2b8"   # flash "¡Guardado!"
GREEN_ACCENT   = "#3a7a3a"   # sparkle ✦ del main menu
GREEN_DOTS     = "#1e4a1e"   # "● ● ●" decorativos


# ── Helpers de fuente ─────────────────────────────────────────────────────────
def font(size: int, weight: str = "normal") -> ctk.CTkFont:
    """Fuente con peso explícito."""
    return ctk.CTkFont(size=size, weight=weight)


def bold(size: int) -> ctk.CTkFont:
    """Atajo para fuente en negrita."""
    return ctk.CTkFont(size=size, weight="bold")


# ── Tamaños comunes ───────────────────────────────────────────────────────────
CORNER_RADIUS_CARD   = 12
CORNER_RADIUS_BTN    = 10
CORNER_RADIUS_ENTRY  = 14
CORNER_RADIUS_BADGE  = 13

HEIGHT_BTN_LG  = 54   # botón principal grande
HEIGHT_BTN_MD  = 46   # botón mediano
HEIGHT_BTN_SM  = 34   # botón pequeño / badge
HEIGHT_ENTRY   = 52   # campo de texto estándar
HEIGHT_CARD    = 72   # tarjeta de menú / historial
