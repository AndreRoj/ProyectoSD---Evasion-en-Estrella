"""Interfaz gráfica para controlar y observar la simulación Aegis-Star.

La ventana ejecuta la simulación como un proceso hijo. Un hilo lee su salida
sin bloquear los controles; el hilo principal procesa los mensajes recibidos y
actualiza la terminal y la matriz desde la misma instantánea de estado.
"""

import json
import os
from pathlib import Path
import platform
import queue
import secrets
import signal
import subprocess
import sys
import threading

import PySimpleGUI as sg

from config import SECTORES


# Las rutas se calculan desde este módulo para que la aplicación funcione
# independientemente de la carpeta desde la que se inicie Python.
DIRECTORIO = Path(__file__).resolve().parent
IMAGE_DIR = DIRECTORIO / "images"
SHIP_IMAGE = IMAGE_DIR / "nave_espacial.png"
EMPTY_IMAGE = IMAGE_DIR / "vacio.png"
METEOR_IMAGE = IMAGE_DIR / "meteorito.png"

# Cada clave identifica la imagen de un sector y cada valor su nombre.
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
AMBER = "#f59e0b"
MUTED = "#9ca3af"
MAX_EVENTOS = 100
# El servidor prefija los mensajes JSON con este texto para distinguirlos
# de las líneas normales de diagnóstico que también aparecen en su salida.
MARCADOR_EVENTO_INTERFAZ = "@@AEGIS_EVENTO@@"
# Tipo de matriz enviado por el servidor: números para sectores y "X" para nave.
Matriz = list[list[int | str]]


def crear_celda(direccion: str) -> sg.Column:
    """Construye la vista de un sector con su imagen y estado de heartbeat.

    Args:
        direccion: Nombre del sector, por ejemplo, ``"NO"`` o ``"E"``.

    Returns:
        Columna de PySimpleGUI con etiqueta, imagen y estado de conexión.
    """
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
            [
                sg.Text(
                    "SIN LATIDO",
                    key=f"-HEARTBEAT-{direccion}-",
                    size=(13, 1),
                    justification="center",
                    text_color=MUTED,
                    background_color=PANEL_BACKGROUND,
                    font=("Arial", 8),
                )
            ],
        ],
        element_justification="center",
        background_color=PANEL_BACKGROUND,
        pad=(3, 3),
    )


def crear_celda_nave() -> sg.Column:
    """Construye la celda central de la matriz donde aparece la nave.

    Returns:
        Columna de PySimpleGUI con la etiqueta y la imagen de la nave.
    """
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
    """Crea y configura la ventana principal de control de la simulación.

    Organiza la matriz de amenazas, el panel de estado y la terminal, además
    de los controles para ingresar/generar la semilla e iniciar, parar o
    reiniciar la simulación.

    Returns:
        Ventana finalizada y lista para recibir eventos de usuario.
    """
    matriz = [
        [crear_celda("NO"), crear_celda("N"), crear_celda("NE")],
        [crear_celda("O"), crear_celda_nave(), crear_celda("E")],
        [crear_celda("SO"), crear_celda("S"), crear_celda("SE")],
    ]
    columna_mapa = [
        [
            sg.Text(
                "ESPERANDO SEMILLA",
                key="-STATUS-",
                font=("Arial", 18, "bold"),
                text_color=AMBER,
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
                "Escribe una semilla y pulsa Correr para iniciar.",
                key="-DETAIL-",
                text_color=AMBER,
                background_color=PANEL_BACKGROUND,
                size=(48, 2),
                expand_x=True,
            )
        ],
        [
            #terminal exclusiva
            sg.Multiline(
                "",
                key="-EVENTS-",
                size=(58, 16),
                disabled=False,
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
                "REGISTRO DE LATIDOS",
                font=("Arial", 11, "bold"),
                text_color=TEXT_COLOR,
                background_color=PANEL_BACKGROUND,
                pad=(0,(5,0))
            )
        ],
        [
            sg.Text(
                "Los heartbeats y estados se actualizan en tiempo real.",
                text_color="#9ca3af",
                background_color=PANEL_BACKGROUND,
                )
        ],
        [
            #terminal exclusiva para latidos
            sg.Multiline(
                "",
                key="-HEARTBEATS-",
                size=(58, 8),  
                disabled=False,
                autoscroll=True,
                text_color=MUTED,
                background_color=BACKGROUND,
                font=("Consolas", 9),
                expand_x=True,
                expand_y=True,
            )
        ]
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
            sg.Text(
                "Semilla:",
                text_color=TEXT_COLOR,
                background_color=BACKGROUND,
                font=("Arial", 10, "bold"),
            ),
            sg.Input("", key="-SEED-", size=(20, 1)),
            sg.Button("Generar aleatoria", key="-RANDOM-SEED-"),
            sg.Button("Correr", key="-RUN-"),
            sg.Button("Detener simulacion", key="-STOP-", disabled=True),
            sg.Button("Reiniciar simulacion", key="-RESTART-"),
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


def leer_salida(
    proceso: subprocess.Popen[str],
    mensajes: queue.Queue[str],
) -> None:
    """Lee la salida del proceso hijo y entrega sus líneas a la GUI.

    Se ejecuta en un hilo de fondo para que la lectura bloqueante de stdout no
    congele la ventana. No modifica widgets: los cambios visuales pertenecen
    al hilo principal de la interfaz.

    Args:
        proceso: Proceso de simulación cuya salida se va a leer.
        mensajes: Cola donde se publican las líneas recibidas.

    Raises:
        RuntimeError: Si el proceso no tiene una tubería de salida configurada.
    """
    if proceso.stdout is None:
        raise RuntimeError("La salida de la simulacion no esta disponible")
    for linea in proceso.stdout:
        mensajes.put(linea.rstrip("\r\n"))


def iniciar_simulacion(semilla: int) -> subprocess.Popen[str]:
    """Inicia la simulación en modo sin interfaz con la semilla indicada.

    El modo sin interfaz evita abrir una segunda ventana. Su salida estándar
    y errores se combinan en una tubería para que la GUI pueda mostrar tanto
    los eventos estructurados como los mensajes de diagnóstico.

    Args:
        semilla: Entero que determina las secuencias pseudoaleatorias.

    Returns:
        El proceso hijo que ejecuta ``simulacion.py``.
    """
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
            "--seed",
            str(semilla),
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


def detener_simulacion(proceso: subprocess.Popen[str]) -> None:
    """Detiene el proceso de simulación y fuerza su cierre si es necesario.

    Primero envía una señal de parada acorde al sistema operativo y espera a
    que el programa cierre sus procesos internos. Si no responde, intenta
    terminarlo y finalmente lo mata para no dejar procesos activos.

    Args:
        proceso: Proceso hijo que se debe detener.
    """
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


def actualizar_matriz(
    window: sg.Window, matriz: Matriz, conectados: set[str]
) -> None:
    """Refleja en las imágenes y etiquetas el estado actual de cada sector.

    La celda central de la nave no pertenece a los ocho sensores. Para cada
    sensor se selecciona la imagen de meteorito o la vacía según la matriz y
    se indica si el servidor lo considera conectado.

    Args:
        window: Ventana cuyos elementos se van a actualizar.
        matriz: Estado de detección de los ocho sectores.
        conectados: Nombres de los sectores que mantienen conexión activa.
    """
    for key, direccion in CELDAS.items():
        fila, columna = SECTORES[direccion]
        imagen = METEOR_IMAGE if matriz[fila][columna] == 1 else EMPTY_IMAGE
        window[key].update(filename=str(imagen), subsample=4)
        conectado = direccion in conectados
        window[f"-HEARTBEAT-{direccion}-"].update(
            "HEARTBEAT OK" if conectado else "SIN LATIDO",
            text_color=GREEN if conectado else MUTED,
        )


def actualizar_evento(window: sg.Window, linea: str) -> str | None:
    """Interpreta un evento del servidor y actualiza la ventana si corresponde.

    Los eventos JSON de heartbeat actualizan la etiqueta del sensor. Los
    eventos de estado contienen una instantánea completa, usada para refrescar
    la matriz, la clasificación y el indicador de peligro en una sola pasada.

    Args:
        window: Ventana que muestra el estado de la simulación.
        linea: Línea recibida desde la salida del proceso hijo.

    Returns:
        Texto descriptivo para agregar a la terminal, o ``None`` si la línea
        no requiere agregar un detalle adicional.

    Raises:
        ValueError: Si el JSON, el tipo de evento o sus datos son inválidos.
    """
    if not linea.startswith(MARCADOR_EVENTO_INTERFAZ):
        return None

    try:
        evento = json.loads(linea[len(MARCADOR_EVENTO_INTERFAZ):])
    except json.JSONDecodeError as error:
        raise ValueError(f"Evento de interfaz invalido: {error}") from error
    if not isinstance(evento, dict):
        raise ValueError("El evento de interfaz debe ser un objeto JSON")

    tipo = evento.get("tipo")
    if tipo == "heartbeat":
        sector = evento.get("sector")
        if sector not in CELDAS.values():
            raise ValueError(f"Sector de heartbeat desconocido: {sector!r}")
        window[f"-HEARTBEAT-{sector}-"].update(
            "HEARTBEAT OK", text_color=GREEN
        )
        return f"[HEARTBEAT] {sector}: latido recibido."

    if tipo != "estado":
        raise ValueError(f"Tipo de evento de interfaz desconocido: {tipo!r}")

    matriz = evento.get("matriz")
    conectados = evento.get("conectados")
    clasificacion = evento.get("clasificacion")
    peligro = evento.get("peligro")
    if (
        not isinstance(matriz, list)
        or len(matriz) != 3
        or any(not isinstance(fila, list) or len(fila) != 3 for fila in matriz)
        or not isinstance(conectados, list)
        or any(sector not in CELDAS.values() for sector in conectados)
        or not isinstance(clasificacion, str)
        or not isinstance(peligro, bool)
    ):
        raise ValueError("El evento de estado contiene datos invalidos")

    actualizar_matriz(window, matriz, set(conectados))
    window["-STATUS-"].update(
        "PELIGRO" if peligro else "A SALVO",
        text_color=RED if peligro else GREEN,
    )
    window["-DETAIL-"].update(
        clasificacion, text_color=RED if peligro else GREEN
    )
    detalle = evento.get("detalle")
    return detalle if isinstance(detalle, str) else None


def leer_semilla(window: sg.Window) -> int | None:
    """Lee y convierte el valor escrito en el campo de semilla.

    Args:
        window: Ventana que contiene el campo ``-SEED-``.

    Returns:
        La semilla como entero, o ``None`` después de mostrar un error si el
        campo está vacío o no contiene un número entero.
    """
    texto = window["-SEED-"].get().strip()
    try:
        return int(texto)
    except ValueError:
        sg.popup_error(
            "Escribe una semilla entera antes de iniciar la simulacion.",
            title="Semilla invalida",
        )
        return None


def reiniciar_presentacion(window: sg.Window) -> None:
    """Devuelve la matriz y los indicadores de la GUI a su estado inicial.

    La matriz queda sin amenazas y todos los sensores aparecen sin latido.
    Este reinicio visual no inicia ni detiene procesos.

    Args:
        window: Ventana cuyos elementos se deben restablecer.
    """
    matriz: Matriz = [
        [0, 0, 0],
        [0, "X", 0],
        [0, 0, 0],
    ]
    actualizar_matriz(window, matriz, set())
    window["-STATUS-"].update("SIMULACION DETENIDA", text_color=AMBER)
    window["-DETAIL-"].update(
        "Escribe una semilla y pulsa Correr para iniciar.",
        text_color=AMBER,
    )


def agregar_a_terminal(
    window: sg.Window, eventos: list[str], mensajes: list[str], key_terminal: str = "-EVENTS-"
) -> None:
    """Agrega mensajes a la terminal visible, conservando solo los recientes.

    Args:
        window: Ventana que contiene el control ``-EVENTS-``.
        eventos: Historial de mensajes que se mantiene en memoria.
        mensajes: Nuevas líneas que se deben anexar al historial.
    """
    eventos.extend(mensaje for mensaje in mensajes if mensaje)
    del eventos[:-MAX_EVENTOS]
    window[key_terminal].update("\n".join(eventos), autoscroll=True)


def iniciar_aplicacion() -> None:
    """Ejecuta el ciclo de eventos de la interfaz hasta que se cierre.

    Gestiona el proceso hijo, la cola de salida y los botones. Las funciones
    auxiliares internas comparten este estado para iniciar, detener o sustituir
    la simulación actual sin dejar que mensajes de la ejecución anterior
    alteren la siguiente.
    """
    window = crear_ventana()
    proceso: subprocess.Popen[str] | None = None
    mensajes: queue.Queue[str] = queue.Queue()
    hilo_salida: threading.Thread | None = None
    eventos: list[str] = []
    latidos: list[str] = []
    contador_latidos: int = 0

    def actualizar_controles() -> None:
        """Activa o desactiva los botones según exista un proceso activo."""
        ejecutando = proceso is not None and proceso.poll() is None
        window["-RUN-"].update(disabled=ejecutando)
        window["-STOP-"].update(disabled=not ejecutando)

    def detener_actual() -> None:
        """Detiene la ejecución vigente y descarta su salida pendiente."""
        nonlocal proceso, hilo_salida
        if proceso is not None:
            detener_simulacion(proceso)
        if hilo_salida is not None:
            hilo_salida.join(timeout=2.0)
        while True:
            try:
                mensajes.get_nowait()
            except queue.Empty:
                break
        proceso = None
        hilo_salida = None
        actualizar_controles()

    def iniciar_con_semilla(semilla: int) -> None:
        """Limpia la vista e inicia una nueva ejecución con ``semilla``."""
        nonlocal proceso, mensajes, hilo_salida, eventos, latidos, contador_latidos
        reiniciar_presentacion(window)
        eventos = []
        latidos = []
        contador_latidos = 0
        window["-EVENTS-"].update("")
        window['-HEARTBEATS-'].update("")
        try:
            proceso = iniciar_simulacion(semilla)
        except OSError as error:
            proceso = None
            actualizar_controles()
            sg.popup_error(
                f"No se pudo iniciar la simulacion: {error}",
                title="Error de inicio",
            )
            return
        mensajes = queue.Queue()
        hilo_salida = threading.Thread(
            target=leer_salida,
            args=(proceso, mensajes),
            name="lector-salida-simulacion",
            daemon=True,
        )
        hilo_salida.start()
        window["-STATUS-"].update("INICIANDO", text_color=AMBER)
        window["-DETAIL-"].update(
            f"Iniciando simulacion con semilla {semilla}.",
            text_color=AMBER,
        )
        actualizar_controles()

    def procesar_mensajes_pendientes() -> list[str]:
        """Drena la cola, aplica eventos de interfaz y devuelve líneas visibles.

        Los mensajes estructurados se usan para actualizar los widgets; las
        líneas normales del proceso se conservan para mostrar diagnósticos.
        """
        recibidos_eventos: list[str] = []
        recibidos_latidos: list[str] = []

        while True:
            try:
                linea = mensajes.get_nowait()
            except queue.Empty:
                break
            try:
                resultado = actualizar_evento(window, linea)
            except ValueError as error:
                resultado = f"[INTERFAZ] {error}"
            if resultado is not None:
                if resultado.startswith("[HEARTBEAT]"):
                    recibidos_latidos.append(resultado)
                else:
                    recibidos_eventos.append(resultado)
            elif not linea.startswith(MARCADOR_EVENTO_INTERFAZ):
                recibidos_eventos.append(linea)
        return recibidos_eventos, recibidos_latidos

    try:
        # PySimpleGUI procesa los clics aquí; el timeout permite revisar la
        # salida del proceso incluso cuando el usuario no interactúa.
        while True:
            evento, _ = window.read(timeout=100)
            if evento == sg.WIN_CLOSED:
                break

            if evento == "-RANDOM-SEED-":
                window["-SEED-"].update(str(secrets.randbelow(2**32)))
            elif evento in ("-RUN-", "-RESTART-"):
                semilla = leer_semilla(window)
                if semilla is not None:
                    if proceso is not None:
                        detener_actual()
                    iniciar_con_semilla(semilla)
            elif evento == "-STOP-" and proceso is not None:
                detener_actual()
                reiniciar_presentacion(window)
                eventos.append("[SIMULACION] Simulacion detenida.")

            nuevos_ev, nuevos_lat = procesar_mensajes_pendientes()
            eventos.extend(nuevos_ev)
            
            for latido in nuevos_lat:
                latidos.append(latido)
                contador_latidos += 1
                if contador_latidos == 8:
                    latidos.append("-" * 40) # <-- Línea separadora
                    contador_latidos = 0

            if proceso is not None and proceso.poll() is not None:
                if hilo_salida is not None:
                    hilo_salida.join(timeout=1.0)
                
                nuevos_ev, nuevos_lat = procesar_mensajes_pendientes()
                eventos.extend(nuevos_ev)
                #Para separar los latidos viejos de los nuevos
                for latido in nuevos_lat:
                    latidos.append(latido)
                    contador_latidos += 1
                    if contador_latidos == 8:
                        latidos.append("-" * 40) # <-- Línea separadora
                        contador_latidos = 0
                
                proceso = None
                hilo_salida = None
                reiniciar_presentacion(window)
                eventos.append("[SIMULACION] Simulacion finalizada.")
                actualizar_controles()

            if eventos or latidos:
                agregar_a_terminal(window, eventos, [], "-EVENTS-")
                agregar_a_terminal(window, latidos, [], "-HEARTBEATS-")
                eventos = eventos[-MAX_EVENTOS:]
                latidos = latidos[-MAX_EVENTOS:]
    finally:
        if proceso is not None:
            detener_actual()
        window.close()
