"""Cliente TCP ejecutable para un sector sensor."""

import json
import random
import socket
import sys
import threading
import time

from config import (
    DURACION_DETECCION,
    HEARTBEAT_INTERVAL,
    HOST,
    INTERVALO_DETECCION,
    PORT,
    PROBABILIDAD_DETECCION,
    SECTORES,
    SEMILLA,
)


def ejecutar_sensor(sector):
    """Conecta el sensor, emite heartbeats y simula detecciones."""
    if sector not in SECTORES:
        raise ValueError(f"Sector desconocido: {sector}")

    generador = random.Random(SEMILLA + hash(sector))
    conexion = socket.create_connection((HOST, PORT), timeout=5.0)
    conexion.settimeout(None)
    lock_envio = threading.Lock()
    parar = threading.Event()

    def enviar(tipo, **datos):
        mensaje = {"tipo": tipo, "sector": sector, **datos}
        contenido = (json.dumps(mensaje) + "\n").encode("utf-8")
        with lock_envio:
            conexion.sendall(contenido)

    def emitir_heartbeats():
        while not parar.is_set():
            try:
                enviar("HEARTBEAT")
            except OSError:
                parar.set()
                return
            if parar.wait(HEARTBEAT_INTERVAL):
                return

    print(f"[SENSOR {sector}] Conectado a {HOST}:{PORT}.", flush=True)
    hilo_heartbeat = threading.Thread(
        target=emitir_heartbeats,
        name=f"heartbeat-{sector}",
        daemon=True,
    )
    hilo_heartbeat.start()

    try:
        while not parar.is_set():
            if generador.random() < PROBABILIDAD_DETECCION:
                enviar("DETECCION", estado=1)
                print(f"[SENSOR {sector}] Objeto detectado.", flush=True)
                if parar.wait(DURACION_DETECCION):
                    break
                enviar("DETECCION", estado=0)
                print(f"[SENSOR {sector}] Objeto liberado.", flush=True)
            if parar.wait(INTERVALO_DETECCION):
                break
    except (BrokenPipeError, ConnectionError, OSError) as error:
        print(f"[SENSOR {sector}] Conexion perdida: {error}.", flush=True)
    except KeyboardInterrupt:
        print(f"\n[SENSOR {sector}] Deteniendo sensor...", flush=True)
    finally:
        parar.set()
        hilo_heartbeat.join(timeout=HEARTBEAT_INTERVAL + 0.5)
        try:
            conexion.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conexion.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"Uso: {sys.argv[0]} <sector>")
    try:
        ejecutar_sensor(sys.argv[1].upper())
    except (OSError, ValueError) as error:
        raise SystemExit(f"No se pudo iniciar el sensor: {error}") from error