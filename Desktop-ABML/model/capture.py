"""
model/capture.py — Captura de pantalla (monitores y ventanas Win32).

Funciones públicas
------------------
get_sources(app_title)         → lista de fuentes disponibles
capture_frame(source, cache)   → (frame_bgr | None, error_str)
"""
import time
import ctypes

import numpy as np
import cv2
import mss
import pygetwindow as gw
import win32gui
import win32ui
import win32con  # noqa: F401  (requerido por win32ui internamente)


def get_sources(app_title: str = "") -> list[str]:
    """
    Devuelve la lista de fuentes de captura disponibles:
    monitores detectados + ventanas abiertas (excluyendo la app misma).
    """
    sources = []
    with mss.mss() as sct:
        for i, monitor in enumerate(sct.monitors[1:], 1):
            sources.append(f"Monitor {i} ({monitor['width']}x{monitor['height']})")
    for title in gw.getAllTitles():
        if title.strip() and title not in ("Program Manager", app_title):
            sources.append(f"Ventana: {title}")
    return sources or ["Monitor 1"]


def _get_monitor_bbox(source: str) -> dict | None:
    idx = int(source.split(" ")[1])
    with mss.mss() as sct:
        monitors = sct.monitors
        return monitors[idx] if idx <= len(monitors) - 1 else monitors[1]


def _capture_monitor(source: str) -> tuple[np.ndarray | None, str]:
    bbox = _get_monitor_bbox(source)
    if not bbox or bbox["width"] <= 0:
        return None, ""
    with mss.mss() as sct:
        shot = sct.grab(bbox)
        frame = np.array(shot)
        if frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        return frame, ""


def _capture_window(source: str, hwnd_cache: dict) -> tuple[np.ndarray | None, str]:
    title = source.replace("Ventana: ", "", 1)

    # Resolver hwnd con caché
    hwnd = hwnd_cache.get(source)
    if hwnd and not win32gui.IsWindow(hwnd):
        del hwnd_cache[source]
        hwnd = None

    if not hwnd:
        wins = gw.getWindowsWithTitle(title)
        if wins:
            hwnd = wins[0]._hWnd
        else:
            kw = title.split(" - ")[-1] if " - " in title else title
            for w in gw.getAllWindows():
                if w.title.strip() and kw.lower() in w.title.lower():
                    hwnd = w._hWnd
                    break
        if hwnd:
            hwnd_cache[source] = hwnd

    if not hwnd:
        return None, ""

    if win32gui.IsIconic(hwnd):
        time.sleep(0.1)
        return None, ""

    l, t, r, b = win32gui.GetClientRect(hwnd)
    w, h = r - l, b - t
    if w <= 0 or h <= 0:
        return None, ""

    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc  = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    bmp     = win32ui.CreateBitmap()
    try:
        bmp.CreateCompatibleBitmap(mfc_dc, w, h)
        save_dc.SelectObject(bmp)
        if ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3) == 1:
            info = bmp.GetInfo()
            data = bmp.GetBitmapBits(True)
            img  = np.frombuffer(data, dtype="uint8").reshape(
                info["bmHeight"], info["bmWidth"], 4
            )
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR), ""
    except IndexError:
        pass
    except Exception as exc:
        return None, str(exc)
    finally:
        win32gui.DeleteObject(bmp.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)

    return None, ""


def capture_frame(source: str, hwnd_cache: dict) -> tuple[np.ndarray | None, str]:
    """
    Captura un frame de la fuente indicada.

    Parámetros
    ----------
    source     : str   — elemento de la lista devuelta por get_sources()
    hwnd_cache : dict  — diccionario mutable de caché de handles de ventana

    Retorna
    -------
    (frame_bgr, error_msg)
        frame_bgr  — np.ndarray BGR o None si no hay frame disponible
        error_msg  — cadena de error (vacía si todo fue bien)
    """
    if source.startswith("Monitor"):
        return _capture_monitor(source)
    if source.startswith("Ventana:"):
        return _capture_window(source, hwnd_cache)
    return None, f"Fuente desconocida: {source}"
