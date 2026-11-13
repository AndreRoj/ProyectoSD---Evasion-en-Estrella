import random
from datetime import datetime


DIRECCIONES = (
    ("noroeste", "NOROESTE"),
    ("norte", "NORTE"),
    ("noreste", "NORESTE"),
    ("este", "ESTE"),
    ("sureste", "SURESTE"),
    ("sur", "SUR"),
    ("suroeste", "SUROESTE"),
    ("oeste", "OESTE"),
)
ETIQUETAS = dict(DIRECCIONES)
MAX_EVENTOS = 100


class ProcesadorDetecciones:
    """Gestiona el estado de amenazas y el historial de eventos."""

    def __init__(self) -> None:
        self._meteoritos: set[str] = set()
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
            grupo[0] for grupo in self.grupos_deteccion if len(grupo) == 1
        )

    @property
    def grupos_deteccion(self) -> tuple[tuple[str, ...], ...]:
        """Agrupa detecciones consecutivas en el orden de los ocho sectores."""
        indices = [
            index
            for index, (direccion, _) in enumerate(DIRECCIONES)
            if direccion in self._meteoritos
        ]
        if not indices:
            return ()

        grupos_indices: list[list[int]] = [[indices[0]]]
        for index in indices[1:]:
            if index == grupos_indices[-1][-1] + 1:
                grupos_indices[-1].append(index)
            else:
                grupos_indices.append([index])

        if (
            len(grupos_indices) > 1
            and (grupos_indices[-1][-1] + 1) % len(DIRECCIONES)
            == grupos_indices[0][0]
        ):
            grupos_indices[0] = grupos_indices[-1] + grupos_indices[0]
            grupos_indices.pop()

        return tuple(
            tuple(DIRECCIONES[index][0] for index in grupo)
            for grupo in grupos_indices
        )

    @property
    def grupos_transito(self) -> tuple[tuple[str, ...], ...]:
        return tuple(
            grupo for grupo in self.grupos_deteccion if len(grupo) >= 2
        )

    def _resumen_clasificacion(self) -> str:
        grupos = self.grupos_deteccion
        if not grupos:
            return "Nave a salvo: no se detectaron meteoritos."

        peligros = [
            ETIQUETAS[grupo[0]] for grupo in grupos if len(grupo) == 1
        ]
        transitos = [
            " → ".join(ETIQUETAS[direccion] for direccion in grupo)
            for grupo in grupos
            if len(grupo) >= 2
        ]
        resumen = []
        if peligros:
            resumen.append(
                f"PELIGRO: detección aislada en {', '.join(peligros)}"
            )
        if transitos:
            resumen.append(
                "Tránsito consecutivo sin amenaza en "
                + "; ".join(transitos)
            )
        return ". ".join(resumen) + "."

    def registrar_evento(self, mensaje: str) -> None:
        hora = datetime.now().strftime("%H:%M:%S")
        self._eventos.append(f"[{hora}] {mensaje}")
        del self._eventos[:-MAX_EVENTOS]

    def procesar_ciclo(self) -> None:
        """Simula un escaneo binario nuevo y evalúa sus sectores consecutivos."""
        cantidad = random.choices(
            (0, 1, 2, 3), weights=(20, 40, 25, 15), k=1
        )[0]
        detectados = random.sample(
            [direccion for direccion, _ in DIRECCIONES], cantidad
        )

        self._meteoritos = set(detectados)
        detecciones = (
            ", ".join(ETIQUETAS[direccion] for direccion in detectados)
            if detectados
            else "ninguna"
        )
        self.registrar_evento(
            f"Escaneo completado. Sectores detectados: {detecciones}. "
            f"{self._resumen_clasificacion()}"
        )

    def simular_deteccion(self) -> None:
        self.procesar_ciclo()

    def alternar_sector(self, direccion: str) -> None:
        if direccion not in ETIQUETAS:
            raise ValueError(f"Dirección desconocida: {direccion}")

        if direccion in self._meteoritos:
            self._meteoritos.remove(direccion)
            self.registrar_evento(
                f"Se retiró el meteorito de {ETIQUETAS[direccion]}. "
                f"{self._resumen_clasificacion()}"
            )
        else:
            self._meteoritos.add(direccion)
            self.registrar_evento(
                f"Se detectó meteorito en {ETIQUETAS[direccion]}. "
                f"{self._resumen_clasificacion()}"
            )