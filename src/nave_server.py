"""Servidor TCP central para la simulacion Aegis-Star."""

import json
import socket
import threading
import time

from config import HOST, MAX_SENSORES, PORT, SECTORES, TIMEOUT_SENSOR

MATRIZ_AMENAZAS = [
    [0, 0, 0],
    [0, "X", 0],
    [0, 0, 0],
]
ULTIMO_HEARTBEAT = {}
SENSORES_CONECTADOS = {}
LOCK_ESTADO = threading.Lock()
PARAR_SERVIDOR = threading.Event()
CONEXIONES = set()
LOCK_CONEXIONES = threading.Lock()
ULTIMA_CLASIFICACION = None


class SectorDuplicadoError(ValueError):
    """Indica que otra conexion ya es propietaria del sector."""


def _clasificar_bajo_lock():
    """Devuelve la categoria actual; requiere LOCK_ESTADO adquirido."""
    detecciones = sum(MATRIZ_AMENAZAS[fila][columna] for fila, columna in SECTORES.values())
    if detecciones == 0:
        return "SIN AMENAZAS"
    if detecciones == 1:
        return "¡ALERTA ROJA DE COLISIÓN INMINENTE!"
    return "TRÁNSITO SEGURO (trayectoria paralela/tangencial sin impacto)"


def _actualizar_clasificacion():
    """Imprime solo al cambiar la categoria para mantener la consola legible."""
    global ULTIMA_CLASIFICACION
    with LOCK_ESTADO:
        clasificacion = _clasificar_bajo_lock()
        if clasificacion == ULTIMA_CLASIFICACION:
            return
        ULTIMA_CLASIFICACION = clasificacion

    print(f"[NAVE] {clasificacion}", flush=True)
    if clasificacion == "¡ALERTA ROJA DE COLISIÓN INMINENTE!":
        print("[NAVE] Maniobra de evasion y escudos activados.", flush=True)
    elif clasificacion.startswith("TRÁNSITO SEGURO"):
        print("[NAVE] ALERTA NO ACTIVADA.", flush=True)


def _procesar_mensaje(mensaje, sector_conexion, conexion):
    """Valida y aplica un mensaje recibido desde un sensor."""
    if not isinstance(mensaje, dict):
        raise ValueError("El mensaje debe ser un objeto JSON")
    tipo = mensaje.get("tipo")
    sector = mensaje.get("sector")
    if not isinstance(sector, str) or sector not in SECTORES:
        raise ValueError("Sector ausente o desconocido")
    if sector_conexion and sector != sector_conexion:
        raise ValueError("Sector ausente, desconocido o distinto al registrado")

    estado = None
    if tipo == "DETECCION":
        estado = mensaje.get("estado")
        if type(estado) is not int or estado not in (0, 1):
            raise ValueError("El estado de deteccion debe ser 0 o 1")
    elif tipo != "HEARTBEAT":
        raise ValueError(f"Tipo de mensaje no soportado: {tipo!r}")

    with LOCK_ESTADO:
        propietario = SENSORES_CONECTADOS.get(sector)
        if propietario is not None and propietario is not conexion:
            raise SectorDuplicadoError(f"El sector {sector} ya tiene una conexion activa")
        if propietario is None:
            SENSORES_CONECTADOS[sector] = conexion
        ULTIMO_HEARTBEAT[sector] = time.monotonic()
        if estado is not None:
            fila, columna = SECTORES[sector]
            MATRIZ_AMENAZAS[fila][columna] = estado

    if estado is not None:
        print(f"[NAVE] Sector {sector}: deteccion={estado}.", flush=True)
        _actualizar_clasificacion()
    return sector


def _atender_sensor(conexion, direccion):
    """Lee mensajes JSON en lineas hasta que el sensor se desconecte."""
    sector_conexion = None
    print(f"[NAVE] Conexion recibida desde {direccion}.", flush=True)
    try:
        with conexion, conexion.makefile("r", encoding="utf-8") as lector:
            for linea in lector:
                try:
                    mensaje = json.loads(linea)
                    sector = _procesar_mensaje(mensaje, sector_conexion, conexion)
                except SectorDuplicadoError as error:
                    print(f"[NAVE] Conexion rechazada: {error}.", flush=True)
                    break
                except (json.JSONDecodeError, ValueError) as error:
                    print(f"[NAVE] Mensaje rechazado desde {direccion}: {error}.", flush=True)
                    continue

                if sector_conexion is None:
                    sector_conexion = sector
                    print(f"[NAVE] Sensor {sector} registrado.", flush=True)
    except (ConnectionError, OSError) as error:
        if not PARAR_SERVIDOR.is_set():
            print(f"[NAVE] Error de conexion {direccion}: {error}.", flush=True)
    finally:
        if sector_conexion is not None:
            with LOCK_ESTADO:
                if SENSORES_CONECTADOS.get(sector_conexion) is conexion:
                    SENSORES_CONECTADOS.pop(sector_conexion, None)
                    ULTIMO_HEARTBEAT.pop(sector_conexion, None)
                    fila, columna = SECTORES[sector_conexion]
                    cambio = MATRIZ_AMENAZAS[fila][columna] != 0
                    MATRIZ_AMENAZAS[fila][columna] = 0
                else:
                    cambio = False
            if cambio:
                print(f"[NAVE] Sensor {sector_conexion} desconectado; estado reiniciado.", flush=True)
                _actualizar_clasificacion()
        with LOCK_CONEXIONES:
            CONEXIONES.discard(conexion)


def _monitorear_heartbeats():
    """Marca sensores sin latido reciente como desconectados."""
    while not PARAR_SERVIDOR.wait(0.5):
        ahora = time.monotonic()
        fallos = []
        with LOCK_ESTADO:
            for sector, ultimo in tuple(ULTIMO_HEARTBEAT.items()):
                if ahora - ultimo > TIMEOUT_SENSOR:
                    ULTIMO_HEARTBEAT.pop(sector, None)
                    conexion = SENSORES_CONECTADOS.pop(sector, None)
                    fila, columna = SECTORES[sector]
                    MATRIZ_AMENAZAS[fila][columna] = 0
                    fallos.append((sector, conexion))

        for sector, conexion in fallos:
            print(f"[NAVE] FALLO: sensor {sector} sin heartbeat; marcado desconectado.", flush=True)
            _actualizar_clasificacion()
            if conexion is not None:
                try:
                    conexion.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                conexion.close()


def iniciar_servidor():
    """Inicia el listener y atiende hasta ocho sensores concurrentes."""
    monitor = threading.Thread(target=_monitorear_heartbeats, name="monitor-heartbeats", daemon=True)
    monitor.start()
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        servidor.bind((HOST, PORT))
        servidor.listen(MAX_SENSORES)
        servidor.settimeout(0.5)
        print(f"[NAVE] Escuchando en {HOST}:{PORT}.", flush=True)
        _actualizar_clasificacion()

        while not PARAR_SERVIDOR.is_set():
            try:
                conexion, direccion = servidor.accept()
            except socket.timeout:
                continue

            with LOCK_CONEXIONES:
                if len(CONEXIONES) >= MAX_SENSORES:
                    conexion.close()
                    print("[NAVE] Limite de sensores alcanzado; conexion rechazada.", flush=True)
                    continue
                CONEXIONES.add(conexion)

            hilo = threading.Thread(
                target=_atender_sensor,
                args=(conexion, direccion),
                name=f"sensor-{direccion[0]}:{direccion[1]}",
                daemon=True,
            )
            hilo.start()
    except KeyboardInterrupt:
        print("\n[NAVE] Cerrando servidor...", flush=True)
    finally:
        PARAR_SERVIDOR.set()
        servidor.close()
        with LOCK_CONEXIONES:
            conexiones = tuple(CONEXIONES)
        for conexion in conexiones:
            try:
                conexion.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            conexion.close()
        monitor.join(timeout=1.0)


if __name__ == "__main__":
    iniciar_servidor()