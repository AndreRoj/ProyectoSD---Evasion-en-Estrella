import os
from pathlib import Path
import platform
import queue
import re
import signal
import subprocess
import sys
import threading
from time import monotonic

import PySimpleGUI as sg


DIRECTORIO = Path(__file__).resolve().parent
IMAGE_DIR = DIRECTORIO / "images"
SHIP_IMAGE = IMAGE_DIR / "nave_espacial.png"
EMPTY_IMAGE = IMAGE_DIR / "vacio.png"
METEOR_IMAGE = IMAGE_DIR / "meteorito.png"

CELDAS = {
    f"-CELL-{direction}-": direction
    for row in (("NO", "N", "NE"), ("O", "E"), ("SO", "S", "SE"))
    for direction in row
}

BACKGROUND = "#101827"
PANEL_BACKGROUND = "#182437"
TEXT_COLOR = "#e5e7eb"
GREEN = "#22c55e"
RED = "#ef4444"
INTERVALO_AVISO = 3.0
MAX_EVENTOS = 100
PATRON_FILA = re.compile(r"^\s*([01X])\s+([01X])\s+([01X])\s*$")
Matriz = tuple[tuple[int | str, ...], ...]


def crear_celda(direccion: str) -> sg.Column:
    return sg.Column(
        [
            [
                sg.Text(
                    direccion,
                    size=(8, 1),
                    justification="center",
                    text_color=TEXT_COLOR,
                    background_color=PANEL_BACKGROUND,
                    font=("Arial", 10, "bold"),
                )
            ],
            [
                sg.Image(
                    filename=str(EMPTY_IMAGE),
                    subsample=4,
                    key=f"-CELL-{direccion}-",
                    background_color=PANEL_BACKGROUND,
                    pad=(3, 3),
                )
            ],
        ],
        element_justification="center",
        background_color=PANEL_BACKGROUND,
        pad=(3, 3),
    )


def crear_celda_nave() -> sg.Column:
    return sg.Column(
        [
            [
                sg.Text(
                    "NAVE",
                    size=(8, 1),
                    justification="center",
                    text_color=TEXT_COLOR,
                    background_color=PANEL_BACKGROUND,
                    font=("Arial", 10, "bold"),
                )
            ],
            [
                sg.Image(
                    filename=str(SHIP_IMAGE),
                    subsample=4,
                    background_color=PANEL_BACKGROUND,
                    pad=(3, 3),
                )
            ],
        ],
        element_justification="center",
        background_color=PANEL_BACKGROUND,
        pad=(3, 3),
    )


def crear_ventana() -> sg.Window:
    matriz = [
        [crear_celda("NO"), crear_celda("N"), crear_celda("NE")],
        [crear_celda("O"), crear_celda_nave(), crear_celda("E")],
        [crear_celda("SO"), crear_celda("S"), crear_celda("SE")],
    ]
    columna_mapa = [
        [
            sg.Text(
                "A SALVO",
                key="-STATUS-",
                font=("Arial", 18, "bold"),
                text_color=GREEN,
                background_color=PANEL_BACKGROUND,
                justification="center",
                expand_x=True,
            )
        ],
        [
            sg.Text(
                "MATRIZ DE AMENAZAS",
                font=("Arial", 13, "bold"),
                text_color=TEXT_COLOR,
                background_color=PANEL_BACKGROUND,
            )
        ],
        *matriz,
    ]
    columna_terminal = [
        [
            sg.Text(
                "ESTADO DE LA TERMINAL",
                font=("Arial", 13, "bold"),
                text_color=TEXT_COLOR,
                background_color=PANEL_BACKGROUND,
            )
        ],
        [
            sg.Text(
                "Iniciando simulación...",
                key="-DETAIL-",
                text_color=GREEN,
                background_color=PANEL_BACKGROUND,
                size=(48, 2),
                expand_x=True,
            )
        ],
        [
            sg.Multiline(
                "",
                key="-EVENTS-",
                size=(58, 24),
                disabled=True,
                autoscroll=True,
                text_color=TEXT_COLOR,
                background_color=BACKGROUND,
                font=("Consolas", 9),
                expand_x=True,
                expand_y=True,
            )
        ],
        [
            sg.Text(
                f"Cada estado de la matriz se muestra durante {int(INTERVALO_AVISO)} segundos.",
                text_color="#9ca3af",
                background_color=PANEL_BACKGROUND,
            )
        ],
    ]
    layout = [
        [
            sg.Text(
                "SISTEMA DE EVASIÓN EN ESTRELLA",
                font=("Arial", 18, "bold"),
                text_color=TEXT_COLOR,
                background_color=BACKGROUND,
                expand_x=True,
            )
        ],
        [
            sg.Column(
                columna_mapa,
                background_color=PANEL_BACKGROUND,
                pad=(8, 8),
                vertical_alignment="top",
            ),
            sg.VSeparator(),
            sg.Column(
                columna_terminal,
                background_color=PANEL_BACKGROUND,
                pad=(8, 8),
                expand_x=True,
                expand_y=True,
                vertical_alignment="top",
            ),
        ],
    ]
    return sg.Window(
        "Detección y evasión en estrella",
        layout,
        finalize=True,
        size=(1000, 690),
        resizable=True,
        background_color=BACKGROUND,
        margins=(16, 14),
        font=("Arial", 10),
    )


def _leer_salida(
    proceso: subprocess.Popen[str],
    mensajes: queue.Queue[str],
    avisos: queue.Queue[Matriz],
) -> None:
    filas: list[tuple[int | str, ...]] = []
    for linea in proceso.stdout:
        texto = linea.rstrip("\r\n")
        mensajes.put(texto)
        coincidencia = PATRON_FILA.fullmatch(texto)
        if coincidencia:
            fila = tuple(
                valor if valor == "X" else int(valor)
                for valor in coincidencia.groups()
            )
            filas.append(fila)
            if len(filas) == 3:
                avisos.put(tuple(filas))
                filas.clear()
        elif texto.strip():
            filas.clear()


def _iniciar_simulacion() -> subprocess.Popen[str]:
    entorno = os.environ.copy()
    entorno["PYTHONIOENCODING"] = "utf-8"
    opciones: dict[str, int | bool] = {}
    if platform.system() == "Windows":
        opciones["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        opciones["start_new_session"] = True
    return subprocess.Popen(
        [
            sys.executable,
            str(DIRECTORIO / "simulacion.py"),
            "--headless",
        ],
        cwd=DIRECTORIO,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=entorno,
        **opciones,
    )


def _detener_simulacion(proceso: subprocess.Popen[str]) -> None:
    if proceso.poll() is not None:
        return
    try:
        evento = (
            signal.CTRL_BREAK_EVENT
            if platform.system() == "Windows"
            else signal.SIGINT
        )
        proceso.send_signal(evento)
    except (OSError, ValueError):
        proceso.terminate()
    try:
        proceso.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proceso.terminate()
        try:
            proceso.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proceso.kill()
            proceso.wait()


def _texto_estado(matriz: Matriz) -> tuple[str, bool]:
    detecciones = sum(valor == 1 for fila in matriz for valor in fila)
    if detecciones == 1:
        return "¡ALERTA ROJA DE COLISIÓN INMINENTE!", True
    if detecciones > 1:
        return "TRÁNSITO SEGURO (trayectoria paralela/tangencial sin impacto)", False
    return "SIN AMENAZAS", False


def _actualizar_matriz(
    window: sg.Window, matriz: Matriz
) -> None:
    posiciones = {
        "NO": (0, 0),
        "N": (0, 1),
        "NE": (0, 2),
        "O": (1, 0),
        "E": (1, 2),
        "SO": (2, 0),
        "S": (2, 1),
        "SE": (2, 2),
    }
    for key, direccion in CELDAS.items():
        fila, columna = posiciones[direccion]
        imagen = METEOR_IMAGE if matriz[fila][columna] == 1 else EMPTY_IMAGE
        window[key].update(filename=str(imagen), subsample=4)


def iniciar_aplicacion() -> None:
    window = crear_ventana()
    try:
        proceso = _iniciar_simulacion()
    except OSError:
        window.close()
        raise
    mensajes: queue.Queue[str] = queue.Queue()
    avisos: queue.Queue[Matriz] = queue.Queue()
    hilo_salida = threading.Thread(
        target=_leer_salida,
        args=(proceso, mensajes, avisos),
        name="lector-salida-simulacion",
        daemon=True,
    )
    hilo_salida.start()

    eventos: list[str] = []
    eventos_pendientes: list[str] = []
    proximo_aviso = monotonic()
    proxima_actualizacion_terminal = monotonic()
    try:
        while True:
            evento, _ = window.read(timeout=100)
            if evento == sg.WIN_CLOSED:
                break

            while True:
                try:
                    linea = mensajes.get_nowait()
                except queue.Empty:
                    break
                if linea:
                    eventos_pendientes.append(linea)

            ahora = monotonic()
            if eventos_pendientes and ahora >= proxima_actualizacion_terminal:
                eventos.extend(eventos_pendientes)
                eventos = eventos[-MAX_EVENTOS:]
                eventos_pendientes.clear()
                window["-EVENTS-"].update(
                    "\n".join(eventos), autoscroll=True
                )
                proxima_actualizacion_terminal = (
                    ahora + INTERVALO_AVISO
                )

            if not avisos.empty() and ahora >= proximo_aviso:
                matriz = avisos.get()
                estado, peligro = _texto_estado(matriz)
                _actualizar_matriz(window, matriz)
                window["-STATUS-"].update(
                    "PELIGRO" if peligro else "A SALVO",
                    text_color=RED if peligro else GREEN,
                )
                window["-DETAIL-"].update(
                    estado, text_color=RED if peligro else GREEN
                )
                proximo_aviso = ahora + INTERVALO_AVISO

            if proceso.poll() is not None:
                window["-DETAIL-"].update(
                    "La simulación terminó. Cierra la ventana para salir.",
                    text_color=RED,
                )
    finally:
        _detener_simulacion(proceso)
        window.close()
