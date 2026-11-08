import queue
import socket
import threading


HOST = "127.0.0.1"
PORT = 7000
APODO = "SISTEMA-RADAR"
INTERVALO_RECONEXION = 2


class ClienteRed:
    """Cliente TCP de chat con recepción y reconexión en segundo plano."""

    def __init__(self, apodo: str = APODO) -> None:
        self._apodo = apodo
        self._salida: queue.Queue[str] = queue.Queue()
        self._eventos: queue.Queue[tuple[str, str]] = queue.Queue()
        self._detener = threading.Event()
        self._socket_lock = threading.Lock()
        self._socket: socket.socket | None = None
        self._hilo: threading.Thread | None = None

    def iniciar(self) -> None:
        if self._hilo is not None:
            raise RuntimeError("El cliente de red ya fue iniciado.")

        self._hilo = threading.Thread(
            target=self._ejecutar,
            name="cliente-red",
            daemon=True,
        )
        self._hilo.start()

    def enviar(self, mensaje: str) -> None:
        if self._detener.is_set():
            raise RuntimeError("No se puede enviar: el cliente está cerrado.")
        self._salida.put(mensaje)

    def obtener_eventos(self) -> list[tuple[str, str]]:
        eventos = []
        while True:
            try:
                eventos.append(self._eventos.get_nowait())
            except queue.Empty:
                return eventos

    def cerrar(self) -> None:
        self._detener.set()
        with self._socket_lock:
            conexion = self._socket
        if conexion is not None:
            try:
                conexion.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

        if self._hilo is not None:
            self._hilo.join(timeout=3)

    def _ejecutar(self) -> None:
        desconexion_reportada = False
        mensaje_pendiente: str | None = None

        while not self._detener.is_set():
            conexion = None
            conectado = False
            try:
                conexion = socket.create_connection(
                    (HOST, PORT),
                    timeout=2,
                )
                conexion.settimeout(0.5)
                with self._socket_lock:
                    self._socket = conexion

                conexion.sendall(f"{self._apodo}\n".encode("utf-8"))
                conectado = True
                desconexion_reportada = False
                self._eventos.put(
                    ("estado", f"Conectado al chat en {HOST}:{PORT}.")
                )
                buffer = b""

                while not self._detener.is_set():
                    if mensaje_pendiente is None:
                        try:
                            mensaje_pendiente = self._salida.get_nowait()
                        except queue.Empty:
                            pass
                    if mensaje_pendiente is not None:
                        conexion.sendall(
                            f"{mensaje_pendiente}\n".encode("utf-8")
                        )
                        mensaje_pendiente = None

                    try:
                        datos = conexion.recv(4096)
                    except socket.timeout:
                        continue
                    if not datos:
                        raise ConnectionError("El servidor cerró la conexión.")

                    buffer += datos
                    while b"\n" in buffer:
                        linea, buffer = buffer.split(b"\n", 1)
                        mensaje = linea.decode("utf-8", errors="replace").rstrip(
                            "\r"
                        )
                        if mensaje:
                            self._eventos.put(("mensaje", mensaje))
            except OSError as error:
                if not self._detener.is_set():
                    if conectado:
                        detalle = f"Se perdió la conexión con el chat: {error}"
                    elif not desconexion_reportada:
                        detalle = (
                            f"No se pudo conectar al chat ({error}); "
                            "se reintentará."
                        )
                    else:
                        detalle = ""

                    if detalle:
                        self._eventos.put(("estado", detalle))
                    desconexion_reportada = True
            finally:
                if conexion is not None:
                    with self._socket_lock:
                        if self._socket is conexion:
                            self._socket = None
                    conexion.close()

            if not self._detener.is_set():
                self._detener.wait(INTERVALO_RECONEXION)
