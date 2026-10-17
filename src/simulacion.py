"""Lanza la nave y los ocho sensores como procesos independientes."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from config import SECTORES

DIRECTORIO = Path(__file__).resolve().parent
PYTHON = sys.executable


def _detener_procesos(procesos):
    """Solicita el cierre y fuerza la terminacion si un proceso no responde."""
    for proceso in reversed(procesos):
        if proceso.poll() is None:
            try:
                evento = signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT
                proceso.send_signal(evento)
            except (OSError, ValueError):
                proceso.terminate()
    for proceso in reversed(procesos):
        if proceso.poll() is None:
            try:
                proceso.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proceso.kill()
                proceso.wait()


def main():
    procesos = []
    try:
        entorno = os.environ.copy()
        entorno["PYTHONHASHSEED"] = "0"
        opciones_proceso = {"cwd": DIRECTORIO, "env": entorno}
        if os.name == "nt":
            opciones_proceso["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
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
                [PYTHON, str(DIRECTORIO / "nodo_sensor.py"), sector],
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
    main()