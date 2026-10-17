"""Configuracion compartida de Aegis-Star 8-Sector."""

HOST = "127.0.0.1"
PORT = 65432

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

TIMEOUT_SENSOR = 7.0
HEARTBEAT_INTERVAL = 3.0
SEMILLA = 42
INTERVALO_DETECCION = 5.0
DURACION_DETECCION = 2.0
PROBABILIDAD_DETECCION = 0.35
MAX_SENSORES = len(SECTORES)
