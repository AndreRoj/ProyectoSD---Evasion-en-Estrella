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

Para instalar la dependencia y ejecutar la interfaz desde la raíz del proyecto:

```bash
python -m pip install -r requirements.txt
python main.py
```

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
