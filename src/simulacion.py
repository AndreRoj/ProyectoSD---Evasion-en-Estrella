"""Punto de entrada y coordinador de procesos de la simulación.

En modo gráfico abre la GUI; en modo ``--headless`` inicia el servidor y los
ocho procesos sensores, comparte la semilla y se encarga de cerrarlos juntos.
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from config import SECTORES, SEMILLA

# Los programas hijos se buscan junto a este archivo, no en la carpeta actual
# desde la que el usuario pudo haber iniciado VS Code.
DIRECTORIO = Path(__file__).resolve().parent
PYTHON = sys.executable


def _detener_procesos(procesos):
    """Cierra todos los procesos hijos y espera a que terminen.

    Primero solicita su terminación, luego les da un breve plazo para salir
    limpiamente y, por último, fuerza el cierre de los que sigan ejecutándose.
    El plazo compartido evita esperar varios segundos por cada proceso.

    Args:
        procesos: Lista con el servidor y los procesos de los sensores.
    """
    for proceso in reversed(procesos):
        if proceso.poll() is None:
            if os.name == "nt":
                proceso.terminate()
            else:
                try:
                    proceso.send_signal(signal.SIGINT)
                except (OSError, ValueError):
                    proceso.terminate()

    limite = time.monotonic() + 3.0
    for proceso in reversed(procesos):
        if proceso.poll() is None:
            try:
                proceso.wait(timeout=max(0.0, limite - time.monotonic()))
            except subprocess.TimeoutExpired:
                continue

    for proceso in reversed(procesos):
        if proceso.poll() is None:
            proceso.kill()
    for proceso in reversed(procesos):
        proceso.wait()


def main(semilla=SEMILLA):
    """Inicia el servidor y un proceso sensor por cada sector configurado.

    El servidor se inicia primero para que los sensores encuentren sus puertos
    al conectarse. El proceso coordinador sigue activo hasta que un proceso
    termina o se interrumpe la simulación; siempre limpia los hijos al salir.

    Args:
        semilla: Entero que se distribuye a todos los sensores para reproducir
            sus secuencias de detección.
    """
    procesos = []
    try:
        entorno = os.environ.copy()
        entorno["PYTHONHASHSEED"] = "0"
        opciones_proceso = {"cwd": DIRECTORIO, "env": entorno}
        # La nave debe estar escuchando antes de iniciar los clientes.
        servidor = subprocess.Popen(
            [PYTHON, str(DIRECTORIO / "nave_server.py")],
            **opciones_proceso,
        )
        procesos.append(servidor)
        time.sleep(1.0)
        if servidor.poll() is not None:
            raise RuntimeError("El servidor finalizo antes de iniciar los sensores")

        orden_sectores = ("NO", "N", "NE", "O", "E", "SO", "S", "SE")
        for sector in orden_sectores:
            if sector not in SECTORES:
                raise RuntimeError(f"Sector sin configuracion: {sector}")
            proceso = subprocess.Popen(
                [
                    PYTHON,
                    str(DIRECTORIO / "nodo_sensor.py"),
                    sector,
                    "--seed",
                    str(semilla),
                ],
                **opciones_proceso,
            )
            procesos.append(proceso)

        print("[SIMULACION] Nave y ocho sensores activos. Ctrl+C para detenerlos.", flush=True)
        while any(proceso.poll() is None for proceso in procesos):
            if servidor.poll() is not None:
                raise RuntimeError("El servidor se detuvo inesperadamente")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[SIMULACION] Cerrando todos los procesos...", flush=True)
    except RuntimeError as error:
        print(f"[SIMULACION] {error}.", file=sys.stderr, flush=True)
    finally:
        _detener_procesos(procesos)


if __name__ == "__main__":
    # ``--headless`` lo usa la GUI para ejecutar este coordinador como proceso
    # hijo; sin esa opción se abre la ventana interactiva.
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--headless",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--seed", type=int, default=SEMILLA)
    argumentos = parser.parse_args()
    if argumentos.headless:
        main(argumentos.seed)
    else:
        from GUI import iniciar_aplicacion

        iniciar_aplicacion()
