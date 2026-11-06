import random
from datetime import datetime
from pathlib import Path

import PySimpleGUI as sg


IMAGE_DIR = Path(__file__).resolve().parent / "images"
SHIP_IMAGE = IMAGE_DIR / "nave_espacial.png"
EMPTY_IMAGE = IMAGE_DIR / "vacio.png"
METEOR_IMAGE = IMAGE_DIR / "meteorito.png"

BACKGROUND = "#101827"
PANEL_BACKGROUND = "#182437"
TEXT_COLOR = "#e5e7eb"
GREEN = "#22c55e"
RED = "#ef4444"
MAX_EVENTS = 100

DIRECTIONS = (
    ("noroeste", "NOROESTE"),
    ("norte", "NORTE"),
    ("noreste", "NORESTE"),
    ("oeste", "OESTE"),
    ("este", "ESTE"),
    ("suroeste", "SUROESTE"),
    ("sur", "SUR"),
    ("sureste", "SURESTE"),
)
CELL_KEYS = {f"-CELL-{direction}-": direction for direction, _ in DIRECTIONS}
LABELS = dict(DIRECTIONS)


def crear_celda(direction: str) -> sg.Column:
    key = f"-CELL-{direction}-"
    return sg.Column(
        [
            [
                sg.Text(
                    LABELS[direction],
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


def registrar_evento(eventos: list[str], mensaje: str) -> None:
    hora = datetime.now().strftime("%H:%M:%S")
    eventos.append(f"[{hora}] {mensaje}")
    del eventos[:-MAX_EVENTS]


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
                "Pulsa una celda para alternar su estado.",
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
            sg.Button(
                "Despejar campo",
                key="-CLEAR-",
                button_color=("white", "#374151"),
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
                f"Se conservan los últimos {MAX_EVENTS} eventos.",
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
                "La simulación permite probar la interfaz; aún no está conectada a sensores o al sistema distribuido.",
                text_color="#9ca3af",
                background_color=BACKGROUND,
                font=("Arial", 9),
            )
        ],
    ]

    return sg.Window(
        "Detección y evasión en estrella",
        layout,
        size=(1000, 690),
        resizable=True,
        background_color=BACKGROUND,
        margins=(16, 14),
        font=("Arial", 10),
    )


def actualizar_interfaz(
    window: sg.Window, meteoritos: set[str], eventos: list[str]
) -> None:
    for key, direction in CELL_KEYS.items():
        image = METEOR_IMAGE if direction in meteoritos else EMPTY_IMAGE
        window[key].update(filename=str(image), subsample=4)

    window["-COUNT-"].update(f"{len(meteoritos)} / 8 sectores")
    if meteoritos:
        direcciones = ", ".join(
            LABELS[direction]
            for direction, _ in DIRECTIONS
            if direction in meteoritos
        )
        window["-STATUS-"].update("PELIGRO", text_color=RED)
        window["-DETAIL-"].update(
            f"Meteorito detectado en: {direcciones}", text_color=RED
        )
    else:
        window["-STATUS-"].update("A SALVO", text_color=GREEN)
        window["-DETAIL-"].update(
            "Sin meteoritos detectados", text_color=GREEN
        )

    window["-EVENTS-"].update(value="\n".join(eventos), autoscroll=True)


def main() -> None:
    meteoritos: set[str] = set()
    eventos: list[str] = []
    registrar_evento(eventos, "Sistema iniciado; esperando detecciones.")

    window = crear_ventana()
    try:
        actualizar_interfaz(window, meteoritos, eventos)
        while True:
            event, _ = window.read()
            if event in (sg.WIN_CLOSED, "-CLOSE-"):
                break

            if event == "-SIMULATE-":
                disponibles = [
                    direction
                    for direction, _ in DIRECTIONS
                    if direction not in meteoritos
                ]
                if disponibles:
                    cantidad = random.randint(1, min(3, len(disponibles)))
                    detectados = random.sample(disponibles, cantidad)
                    meteoritos.update(detectados)
                    nombres = ", ".join(LABELS[d] for d in detectados)
                    registrar_evento(
                        eventos, f"Se detectó meteorito en: {nombres}."
                    )
                else:
                    registrar_evento(
                        eventos,
                        "Simulación omitida: los ocho sectores ya tienen meteoritos.",
                    )
            elif event == "-CLEAR-":
                if meteoritos:
                    meteoritos.clear()
                    registrar_evento(
                        eventos, "Campo despejado; no quedan meteoritos."
                    )
                else:
                    registrar_evento(
                        eventos, "El campo ya estaba despejado."
                    )
            elif event in CELL_KEYS:
                direction = CELL_KEYS[event]
                if direction in meteoritos:
                    meteoritos.remove(direction)
                    registrar_evento(
                        eventos,
                        f"Se retiró el meteorito de {LABELS[direction]}.",
                    )
                else:
                    meteoritos.add(direction)
                    registrar_evento(
                        eventos,
                        f"Se detectó meteorito en {LABELS[direction]}.",
                    )

            actualizar_interfaz(window, meteoritos, eventos)
    finally:
        window.close()


if __name__ == "__main__":
    main()
