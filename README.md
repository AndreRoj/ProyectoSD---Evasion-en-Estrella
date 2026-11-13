# ProyectoSD - Evasion en Estrella

## Interfaz de detección

La aplicación muestra la nave en el centro de un mapa de ocho sectores. Las
imágenes de los sectores cambian entre espacio vacío y meteorito; el estado
general y el registro de eventos se actualizan con cada detección. El código
está separado entre el punto de entrada, la GUI y los procesos de detección:

- `main.py`: inicia la aplicación.
- `src/GUI.py`: crea la ventana y actualiza la interfaz.
- `src/config.py`: administra los meteoritos y el historial de eventos.
- `src/images/`: contiene las imágenes de la interfaz.

La única dependencia externa es PySimpleGUI. La red usa módulos incluidos con
Python (`socket`, `threading` y `queue`), por lo que no requiere instalar
paquetes adicionales. Para instalar PySimpleGUI y ejecutar desde la raíz:

```bash
python -m pip install -r requirements.txt
python main.py
```

La aplicación también se conecta en segundo plano al chat TCP en `127.0.0.1:7000`
con el apodo `SISTEMA-RADAR`. El protocolo usa mensajes UTF-8 terminados en salto
de línea: al conectarse, el cliente envía primero el apodo; después transmite
alertas y cambios de sector, y muestra los mensajes recibidos en el historial de
la interfaz. Si el servidor no está disponible, el cliente reintenta conectarse
cada dos segundos sin bloquear la ventana.

La aplicación realiza un escaneo automático cada dos segundos y representa
cada sector como una detección binaria (meteorito presente o ausente). La
evaluación sigue el enunciado: un único sector detectado, aislado de los demás
en el orden circular NO, N, NE, E, SE, S, SO, O, activa **PELIGRO**. Dos o más
sectores detectados consecutivamente en ese orden forman un tránsito paralelo
o tangencial y no activan la alarma. Si un escaneo contiene tanto sectores
aislados como grupos consecutivos, se informa el tránsito, pero la nave queda
en **PELIGRO** por los sectores aislados. El botón **Simular detección**
ejecuta un ciclo de inmediato; pulsar una celda agrega o retira una detección y
recalcula el estado usando la misma regla. La simulación no está conectada a
sensores reales.

## Chat de operadores

Para activar la comunicación del radar, inicia el servidor en una terminal
desde la raíz del proyecto:

```bash
python server.py
```

En otra terminal, inicia la interfaz con `python main.py`. Cada operador humano
puede abrir una terminal adicional y ejecutar:

```bash
python client.py
```

El servidor escucha en `127.0.0.1:7000`. En el cliente de consola, escribe
mensajes para enviarlos a todos, usa `/w <usuario> <mensaje>` para enviar uno
privado y `/salir` para desconectarte.
