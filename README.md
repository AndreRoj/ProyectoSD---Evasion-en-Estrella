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

La aplicación realiza un escaneo automático cada dos segundos. En cada ciclo
puede detectar cero o varios meteoritos y clasificar su trayectoria como
impacto, paralela o tangencial. Solo una trayectoria de impacto cambia el
estado de la nave a **PELIGRO**; los pasos paralelos y tangenciales se muestran
en el mapa y en el reporte, pero mantienen el estado **A SALVO**. El botón
**Simular detección** ejecuta un ciclo de inmediato. Al pulsar una celda se
agrega o retira un meteorito manualmente; los agregados manuales se consideran
posibles impactos. La simulación no está conectada a sensores reales.
