"""Cliente TCP que simula un sensor de un sector de la nave.

Cada instancia mantiene su propia secuencia pseudoaleatoria y envía al
servidor tanto latidos periódicos como cambios en su estado de detección.
"""

import json
import random
import socket
import threading

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


def ejecutar_sensor(sector, semilla=SEMILLA):
    """Conecta un sensor, envía heartbeats y produce detecciones aleatorias.

    Se crea un generador independiente por sector, derivado de la semilla
    global, para que las ejecuciones con la misma semilla sean reproducibles.
    Un hilo de fondo mantiene los heartbeats mientras el hilo principal
    simula detecciones y sus períodos de duración.

    Args:
        sector: Nombre del sector que representa este proceso sensor.
        semilla: Semilla base para generar la secuencia pseudoaleatoria.

    Raises:
        ValueError: Si el sector no forma parte de la configuración.
        OSError: Si no se puede establecer o mantener la conexión TCP.
    """
    if sector not in SECTORES:
        raise ValueError(f"Sector desconocido: {sector}")

    indice_sector = tuple(SECTORES).index(sector)
    generador = random.Random(semilla + indice_sector)
    conexion = socket.create_connection((HOST, PORT), timeout=5.0)
    conexion.settimeout(None)
    lock_envio = threading.Lock()
    parar = threading.Event()

    def enviar(tipo, **datos):
        """Serializa y envía una línea JSON protegida por un lock.

        El lock evita que los mensajes del hilo de heartbeat se intercalen con
        los mensajes de detección enviados por el hilo principal.
        """
        mensaje = {"tipo": tipo, "sector": sector, **datos}
        contenido = (json.dumps(mensaje) + "\n").encode("utf-8")
        with lock_envio:
            conexion.sendall(contenido)

    def emitir_heartbeats():
        """Envía latidos al servidor hasta pedir la parada o perder conexión."""
        while not parar.is_set():
            try:
                enviar("HEARTBEAT")
            except OSError:
                parar.set()
                return
            if parar.wait(HEARTBEAT_INTERVAL):
                return

    print(f"[SENSOR {sector}] Conectado a {HOST}:{PORT}.", flush=True)
    # El heartbeat usa un hilo independiente para seguir enviándose mientras
    # el sensor espera a que termine una detección.
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
                print(f"[SENSOR {sector}] Zona libre.", flush=True)
            if parar.wait(INTERVALO_DETECCION):
                break
    except (BrokenPipeError, ConnectionError, OSError) as error:
        print(f"[SENSOR {sector}] Conexion perdida: {error}.", flush=True)
    except KeyboardInterrupt:
        print(f"\n[SENSOR {sector}] Deteniendo sensor...", flush=True)
    finally:
        # Detener el hilo antes de cerrar su socket evita nuevos envíos durante
        # la limpieza de la conexión.
        parar.set()
        hilo_heartbeat.join(timeout=HEARTBEAT_INTERVAL + 0.5)
        try:
            conexion.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conexion.close()


if __name__ == "__main__":
    # Cada proceso sensor recibe su sector y la misma semilla de la simulación.
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("sector")
    parser.add_argument("--seed", type=int, default=SEMILLA)
    argumentos = parser.parse_args()
    try:
        ejecutar_sensor(argumentos.sector.upper(), argumentos.seed)
    except (OSError, ValueError) as error:
        raise SystemExit(f"No se pudo iniciar el sensor: {error}") from error