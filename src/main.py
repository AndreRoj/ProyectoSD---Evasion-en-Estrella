import PySimpleGUI as sg

# 1. Definir el diseño (layout)
layout = [
    [sg.Text("Panel de Control del Sistema")],
    [sg.Image(filename="src/images/nave_espacial.png", key="-IMAGEN-")],  # Agrega la imagen aquí
    #[sg.Image(size = (20,20), key="-IMAGEN-")]
    [sg.Button("Cerrar")]
]

# 2. Crear la ventana
window = sg.Window("Interfaz de Nave", layout)

# 3. Bucle de eventos
while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == "Cerrar":
        break

window.close()