import random
from datetime import datetime


DIRECCIONES = (
    ("noroeste", "NOROESTE"),
    ("norte", "NORTE"),
    ("noreste", "NORESTE"),
    ("oeste", "OESTE"),
    ("este", "ESTE"),
    ("suroeste", "SUROESTE"),
    ("sur", "SUR"),
    ("sureste", "SURESTE"),
)
ETIQUETAS = dict(DIRECCIONES)
MAX_EVENTOS = 100
TRAYECTORIAS = ("impacto", "paralelo", "tangencial")


class ProcesadorDetecciones:
    """Gestiona el estado de amenazas y el historial de eventos."""

    def __init__(self) -> None:
        self._meteoritos: set[str] = set()
        self._trayectorias: dict[str, str] = {}
        self._eventos: list[str] = []
        self.registrar_evento(
            "Monitoreo iniciado; se realizará un escaneo cada 2 segundos."
        )

    @property
    def meteoritos(self) -> frozenset[str]:
        return frozenset(self._meteoritos)

    @property
    def eventos(self) -> tuple[str, ...]:
        return tuple(self._eventos)

    @property
    def peligros(self) -> frozenset[str]:
        return frozenset(
            direccion
            for direccion, trayectoria in self._trayectorias.items()
            if trayectoria == "impacto"
        )

    @property
    def trayectorias(self) -> dict[str, str]:
        return self._trayectorias.copy()

    def registrar_evento(self, mensaje: str) -> None:
        hora = datetime.now().strftime("%H:%M:%S")
        self._eventos.append(f"[{hora}] {mensaje}")
        del self._eventos[:-MAX_EVENTOS]

    def procesar_ciclo(self) -> None:
        """Simula un nuevo escaneo y reemplaza las detecciones anteriores."""
        cantidad = random.choices(
            (0, 1, 2, 3), weights=(20, 40, 25, 15), k=1
        )[0]
        detectados = random.sample(
            [direccion for direccion, _ in DIRECCIONES], cantidad
        )

        self._meteoritos = set(detectados)
        self._trayectorias = {
            direccion: random.choices(
                TRAYECTORIAS, weights=(30, 35, 35), k=1
            )[0]
            for direccion in detectados
        }

        if not detectados:
            self.registrar_evento(
                "Escaneo completado: no se detectaron meteoritos. Nave a salvo."
            )
            return

        detalles = "; ".join(
            f"{ETIQUETAS[direccion]} ({self._trayectorias[direccion]})"
            for direccion in detectados
        )
        if self.peligros:
            zonas_peligrosas = ", ".join(
                ETIQUETAS[direccion]
                for direccion in detectados
                if direccion in self.peligros
            )
            self.registrar_evento(
                f"PELIGRO: posible trayectoria de impacto en {zonas_peligrosas}. "
                f"Detecciones: {detalles}."
            )
        else:
            self.registrar_evento(
                "Nave a salvo: meteoritos con trayectoria paralela o "
                f"tangencial. Detecciones: {detalles}."
            )

    def simular_deteccion(self) -> None:
        self.procesar_ciclo()

    def alternar_sector(self, direccion: str) -> None:
        if direccion not in ETIQUETAS:
            raise ValueError(f"Dirección desconocida: {direccion}")

        if direccion in self._meteoritos:
            self._meteoritos.remove(direccion)
            self._trayectorias.pop(direccion, None)
            self.registrar_evento(
                f"Se retiró el meteorito de {ETIQUETAS[direccion]}."
            )
        else:
            self._meteoritos.add(direccion)
            self._trayectorias[direccion] = "impacto"
            self.registrar_evento(
                f"PELIGRO: meteorito agregado manualmente en "
                f"{ETIQUETAS[direccion]} (trayectoria de impacto)."
            )

    def despejar_campo(self) -> None:
        if self._meteoritos:
            self._meteoritos.clear()
            self._trayectorias.clear()
            self.registrar_evento("Campo despejado; no quedan meteoritos.")
        else:
            self.registrar_evento("El campo ya estaba despejado.")
