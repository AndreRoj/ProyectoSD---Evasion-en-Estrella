# Aegis-Star 8-Sector

Simulacion local de una nave central y ocho sensores distribuidos usando TCP,
JSON delimitado por lineas y un hilo de atencion por conexion.

## Requisitos

- Python 3.9 o posterior.
- No requiere dependencias externas.

## Ejecucion completa

Desde la raiz del repositorio:

```powershell
python src/simulacion.py
```

El script inicia primero el servidor y, un segundo despues, los sensores
`NO`, `N`, `NE`, `O`, `E`, `SO`, `S` y `SE` como procesos independientes.
Presiona `Ctrl+C` para detener todos los procesos.

Tambien se pueden iniciar manualmente en terminales separadas:

```powershell
python src/nave_server.py
python src/nodo_sensor.py N
```

## Configuracion y protocolo

`src/config.py` define `HOST`, `PORT`, los ocho sectores, el timeout y los
intervalos de simulacion. Cada mensaje es un objeto JSON seguido por `\n`:

```json
{"tipo":"HEARTBEAT","sector":"N"}
{"tipo":"DETECCION","sector":"N","estado":1}
```

El estado `0` libera el sector. El servidor mantiene la matriz 3x3 con la nave
en el centro (`X`), actualiza datos compartidos bajo un lock y vigila
los heartbeats en un hilo daemon. Si pasan 7 segundos sin latido, el sector se
marca como desconectado y su deteccion se reinicia.

## Clasificacion

- Cero detecciones: `SIN AMENAZAS`.
- Una deteccion: alerta roja, maniobra de evasion y escudos.
- Dos o mas detecciones: transito seguro, trayectoria paralela/tangencial y
	alerta no activada.

Los sensores usan `random.Random(SEMILLA + hash(sector))`. El lanzador fija
`PYTHONHASHSEED=0` para que la simulacion sea reproducible entre procesos.

