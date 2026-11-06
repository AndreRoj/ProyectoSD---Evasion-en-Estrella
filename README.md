# ProyectoSD - Evasion en Estrella

## Interfaz de detección

La aplicación muestra la nave en el centro de un mapa de ocho sectores. Las
imágenes de los sectores cambian entre espacio vacío y meteorito; el estado
general y el registro de eventos se actualizan con cada detección.

Para instalar la dependencia y ejecutar la interfaz desde la raíz del proyecto:

```bash
python -m pip install -r requirements.txt
python src/main.py
```

Pulsa **Simular detección** para agregar meteoritos en uno a tres sectores al
azar. También puedes pulsar directamente una celda para alternar su estado y
usar **Despejar campo** para quitar todos los meteoritos. Esta simulación sirve
para probar la interfaz; todavía no está conectada a sensores ni a los procesos
del sistema distribuido.
