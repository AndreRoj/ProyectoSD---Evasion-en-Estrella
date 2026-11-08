from pathlib import Path
from time import monotonic

import PySimpleGUI as sg

from .config import ProcesadorDetecciones

DIRECCIONES = (
    ("noroeste", "NOROESTE"),
    ("norte", "NORTE"),
    ("noreste", "NORESTE"),
    ("este", "ESTE"),
    ("sureste", "SURESTE"),
    ("sur", "SUR"),
    ("suroeste", "SUROESTE"),
    ("oeste", "OESTE"),
)
ETIQUETAS = dict(DIRECCIONES)
MAX_EVENTOS = 100

IMAGE_DIR = Path(__file__).resolve().parent / "images"
SHIP_IMAGE = IMAGE_DIR / "nave_espacial.png"
EMPTY_IMAGE = IMAGE_DIR / "vacio.png"
METEOR_IMAGE = IMAGE_DIR / "meteorito.png"

BACKGROUND = "#101827"
PANEL_BACKGROUND = "#182437"
TEXT_COLOR = "#e5e7eb"
GREEN = "#22c55e"
RED = "#ef4444"

CELL_KEYS = {
    f"-CELL-{direction}-": direction for direction, _ in DIRECCIONES
}


def crear_celda(direction: str) -> sg.Column:
    key = f"-CELL-{direction}-"
    return sg.Column(
        [
            [
                sg.Text(
                    ETIQUETAS[direction],
                    size=(12, 1),
                    justification="center",
                    text_color=TEXT_COLOR,
                    background_color=PANEL_BACKGROUND,
                    font=("Arial", 9, "bold"),
                )
            ],
            [
                sg.Image(
                    filename=str(EMPTY_IMAGE),
                    subsample=4,
                    key=key,
                    enable_events=True,
                    background_color=PANEL_BACKGROUND,
                    pad=(2, 2),
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
                    size=(12, 1),
                    justification="center",
                    text_color=TEXT_COLOR,
                    background_color=PANEL_BACKGROUND,
                    font=("Arial", 9, "bold"),
                )
            ],
            [
                sg.Image(
                    filename=str(SHIP_IMAGE),
                    subsample=4,
                    key="-SHIP-",
                    background_color=PANEL_BACKGROUND,
                    pad=(2, 2),
                )
            ],
        ],
        element_justification="center",
        background_color=PANEL_BACKGROUND,
        pad=(3, 3),
    )


def crear_ventana() -> sg.Window:
    mapa = [
        [
            crear_celda("noroeste"),
            crear_celda("norte"),
            crear_celda("noreste"),
        ],
        [
            crear_celda("oeste"),
            crear_celda_nave(),
            crear_celda("este"),
        ],
        [
            crear_celda("suroeste"),
            crear_celda("sur"),
            crear_celda("sureste"),
        ],
    ]

    columna_mapa = [
        [
            sg.Text(
                "MAPA DE AMENAZAS",
                font=("Arial", 13, "bold"),
                text_color=TEXT_COLOR,
                background_color=PANEL_BACKGROUND,
            )
        ],
        [
            sg.Text(
                "Escaneo automático cada 2 segundos.",
                text_color="#9ca3af",
                background_color=PANEL_BACKGROUND,
            )
        ],
        *mapa,
        [
            sg.Button(
                "Simular detección",
                key="-SIMULATE-",
                button_color=("white", "#2563eb"),
                pad=(4, 10),
            ),
        ],
    ]

    columna_eventos = [
        [
            sg.Text(
                "ACTIVIDAD EN TIEMPO REAL",
                font=("Arial", 13, "bold"),
                text_color=TEXT_COLOR,
                background_color=PANEL_BACKGROUND,
            )
        ],
        [
            sg.Text(
                "Eventos recientes",
                text_color="#9ca3af",
                background_color=PANEL_BACKGROUND,
            )
        ],
        [
            sg.Multiline(
                "",
                key="-EVENTS-",
                size=(43, 21),
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
                f"Se conservan los últimos {MAX_EVENTOS} eventos.",
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
            ),
            sg.Text(
                "A SALVO",
                key="-STATUS-",
                font=("Arial", 14, "bold"),
                text_color=GREEN,
                background_color=BACKGROUND,
            ),
        ],
        [
            sg.Text(
                "Sin meteoritos detectados",
                key="-DETAIL-",
                text_color=GREEN,
                background_color=BACKGROUND,
                expand_x=True,
            ),
            sg.Text(
                "0 / 8 sectores",
                key="-COUNT-",
                text_color=TEXT_COLOR,
                background_color=BACKGROUND,
            ),
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
                columna_eventos,
                background_color=PANEL_BACKGROUND,
                pad=(8, 8),
                expand_x=True,
                expand_y=True,
                vertical_alignment="top",
            ),
        ],
        [
            sg.Text(
                "Un sector aislado activa peligro; detecciones consecutivas representan tránsito.",
                text_color="#9ca3af",
                background_color=BACKGROUND,
                font=("Arial", 9),
            )
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


def actualizar_interfaz(
    window: sg.Window, procesador: ProcesadorDetecciones
) -> None:
    meteoritos = procesador.meteoritos
    peligros = procesador.peligros
    grupos_transito = procesador.grupos_transito
    for key, direction in CELL_KEYS.items():
        image = METEOR_IMAGE if direction in meteoritos else EMPTY_IMAGE
        window[key].update(filename=str(image), subsample=4)

    window["-COUNT-"].update(f"{len(meteoritos)} / 8 sectores")
    direcciones_transito = "; ".join(
        " → ".join(ETIQUETAS[direction] for direction in grupo)
        for grupo in grupos_transito
    )
    if peligros:
        direcciones_peligrosas = ", ".join(
            ETIQUETAS[direction]
            for direction, _ in DIRECCIONES
            if direction in peligros
        )
        window["-STATUS-"].update("PELIGRO", text_color=RED)
        detalle = f"Detección aislada en: {direcciones_peligrosas}"
        if direcciones_transito:
            detalle += f" | Tránsito sin amenaza: {direcciones_transito}"
        window["-DETAIL-"].update(detalle, text_color=RED)
    elif meteoritos:
        window["-STATUS-"].update("A SALVO", text_color=GREEN)
        window["-DETAIL-"].update(
            f"Tránsito consecutivo sin amenaza: {direcciones_transito}",
            text_color=GREEN,
        )
    else:
        window["-STATUS-"].update("A SALVO", text_color=GREEN)
        window["-DETAIL-"].update(
            "Sin meteoritos detectados", text_color=GREEN
        )

    window["-EVENTS-"].update(
        value="\n".join(procesador.eventos), autoscroll=True
    )


def _enviar_alerta_si_corresponde(
    cliente: ClienteRed, procesador: ProcesadorDetecciones
) -> None:
    if not procesador.peligros:
        return

    sectores = ", ".join(
        ETIQUETAS[direccion]
        for direccion, _ in DIRECCIONES
        if direccion in procesador.peligros
    )
    cliente.enviar(
        "[RADAR-ALERTA] ¡Peligro de colisión detectado "
        f"en sector {sectores}!"
    )


def iniciar_aplicacion() -> None:
    procesador = ProcesadorDetecciones()
    window = crear_ventana()
    cliente = ClienteRed()
    try:
        cliente.iniciar()
        actualizar_interfaz(window, procesador)
        proximo_escaneo = monotonic() + 2
        while True:
            event, _ = window.read(timeout=100, timeout_key="-POLL-")
            if event in (sg.WIN_CLOSED, "-CLOSE-"):
                break

            actualizar = False
            ahora = monotonic()
            if event == "-SIMULATE-" or ahora >= proximo_escaneo:
                procesador.simular_deteccion()
                actualizar = True
                if ahora >= proximo_escaneo:
                    proximo_escaneo = ahora + 2
                _enviar_alerta_si_corresponde(cliente, procesador)

            if event in CELL_KEYS:
                direccion = CELL_KEYS[event]
                ya_detectado = direccion in procesador.meteoritos
                procesador.alternar_sector(direccion)
                accion = "Se retiró la detección" if ya_detectado else (
                    "Se detectó un meteorito"
                )
                cliente.enviar(
                    f"[RADAR-SECTOR] {accion} en sector "
                    f"{ETIQUETAS[direccion]}."
                )
                actualizar = True
                _enviar_alerta_si_corresponde(cliente, procesador)

            for tipo, mensaje in cliente.obtener_eventos():
                if tipo == "mensaje":
                    procesador.registrar_evento(f"Servidor: {mensaje}")
                else:
                    procesador.registrar_evento(mensaje)
                actualizar = True

            if actualizar:
                actualizar_interfaz(window, procesador)
    finally:
        cliente.cerrar()
        window.close()
