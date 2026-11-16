"""Parámetros de red y comportamiento compartidos por todos los procesos."""

# Dirección local: el servidor solo acepta conexiones desde este equipo.
HOST = "127.0.0.1"
# Los sensores se conectan al puerto de datos; la GUI usa el puerto de control.
PORT = 65432
CONTROL_PORT = 65433

# Posición de cada sensor en la matriz 3x3; el centro se reserva para la nave.
SECTORES = {
    "NO": (0, 0),
    "N": (0, 1),
    "NE": (0, 2),
    "O": (1, 0),
    "E": (1, 2),
    "SO": (2, 0),
    "S": (2, 1),
    "SE": (2, 2),
}

# Un sensor que supere este tiempo sin enviar heartbeats se considera caído.
TIMEOUT_SENSOR = 7.0
HEARTBEAT_INTERVAL = 3.0
# Se declara la semilla 
SEMILLA = 0
# Período entre decisiones de detección y tiempo que permanece activa una.
INTERVALO_DETECCION = 5.0
DURACION_DETECCION = 5.0
PROBABILIDAD_DETECCION = 0.15
# El servidor rechaza más conexiones simultáneas que sectores disponibles.
MAX_SENSORES = len(SECTORES)