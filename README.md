# ProyectoSD - Evasion en Estrella

## Iniciar la interfaz

Abre el proyecto en VS Code, selecciona **Simulacion Aegis-Star** en
**Run and Debug** y pulsa el botón de reproducir. La configuración ejecuta
`src/simulacion.py` con `src` como carpeta de trabajo. También puedes usar el
botón **Run Python File** con `simulacion.py` abierto.

La primera vez, selecciona en VS Code un intérprete que tenga instaladas las
dependencias de `requirements.txt` (puedes usar **Python: Create Environment**
desde la paleta de comandos). Después, el proyecto se inicia desde el botón de
reproducir sin escribir comandos en la terminal.

La simulación no arranca hasta que se escriba una semilla y se pulse
**Correr**. **Generar aleatoria** crea
una semilla nueva; **Detener simulacion** detiene los procesos y
**Reiniciar simulacion** inicia otra ejecución con la semilla que aparece en
el campo.

La matriz muestra el estado de detección y el heartbeat más reciente de cada
sensor. La interfaz recibe una instantánea completa del servidor con cada
cambio, por lo que las imágenes, la clasificación de peligro y la terminal se
actualizan a partir del mismo evento. Una detección en un sector se clasifica
como peligro; varias detecciones simultáneas se clasifican como tránsito
seguro, de acuerdo con la lógica existente del proyecto.

La misma semilla reproduce la secuencia pseudoaleatoria de detecciones de los
sensores. Para iniciar la simulación sin la interfaz se puede ejecutar
`python simulacion.py --headless --seed 42` desde `src`.