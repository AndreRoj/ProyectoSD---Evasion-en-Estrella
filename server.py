import socket
import threading
from dataclasses import dataclass, field


HOST = "127.0.0.1"
PORT = 7000
BUFFER_SIZE = 4096


@dataclass
class Cliente:
    conexion: socket.socket
    apodo: str
    lock_envio: threading.Lock = field(default_factory=threading.Lock)


clientes: dict[socket.socket, Cliente] = {}
lock_clientes = threading.Lock()


def _enviar(cliente: Cliente, mensaje: str) -> bool:
    datos = f"{mensaje}\n".encode("utf-8")
    try:
        with cliente.lock_envio:
            cliente.conexion.sendall(datos)
        return True
    except OSError:
        return False


def _broadcast(mensaje: str, emisor: socket.socket | None = None) -> None:
    with lock_clientes:
        destinatarios = [
            cliente
            for conexion, cliente in clientes.items()
            if conexion is not emisor
        ]

    for destinatario in destinatarios:
        _enviar(destinatario, mensaje)


def _desconectar(conexion: socket.socket) -> None:
    with lock_clientes:
        cliente = clientes.pop(conexion, None)

    try:
        conexion.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        conexion.close()
    except OSError:
        pass

    if cliente is not None:
        _broadcast(f"* {cliente.apodo} se ha desconectado.")


def _enrutar_mensaje(emisor: Cliente, mensaje: str) -> None:
    if mensaje.startswith("/w "):
        partes = mensaje.split(" ", 2)
        if len(partes) != 3 or not partes[1] or not partes[2]:
            _enviar(emisor, "Uso: /w <usuario> <mensaje>")
            return

        apodo_destino, texto = partes[1], partes[2]
        with lock_clientes:
            destinatario = next(
                (
                    cliente
                    for cliente in clientes.values()
                    if cliente.apodo.casefold() == apodo_destino.casefold()
                ),
                None,
            )

        if destinatario is None:
            _enviar(emisor, f"No se encontró al usuario «{apodo_destino}».")
            return

        _enviar(
            destinatario,
            f"[Privado de {emisor.apodo}] {texto}",
        )
        _enviar(emisor, f"[Privado para {destinatario.apodo}] {texto}")
        return

    _broadcast(f"{emisor.apodo}: {mensaje}", emisor=emisor.conexion)


def _atender_cliente(conexion: socket.socket) -> None:
    buffer = bytearray()
    cliente: Cliente | None = None

    try:
        while True:
            datos = conexion.recv(BUFFER_SIZE)
            if not datos:
                break
            buffer.extend(datos)

            while b"\n" in buffer:
                linea, _, restante = buffer.partition(b"\n")
                buffer = bytearray(restante)
                mensaje = linea.decode("utf-8", errors="replace").rstrip("\r")

                if cliente is None:
                    apodo = mensaje.strip()
                    if not apodo:
                        _enviar(
                            Cliente(conexion, ""),
                            "Error: el apodo no puede estar vacío.",
                        )
                        return

                    cliente = Cliente(conexion, apodo)
                    with lock_clientes:
                        if any(
                            existente.apodo.casefold() == apodo.casefold()
                            for existente in clientes.values()
                        ):
                            cliente = None
                        else:
                            clientes[conexion] = cliente

                    if cliente is None:
                        _enviar(
                            Cliente(conexion, ""),
                            "Error: ese apodo ya está conectado.",
                        )
                        return

                    _broadcast(
                        f"* {apodo} se ha conectado.",
                        emisor=conexion,
                    )
                elif mensaje:
                    _enrutar_mensaje(cliente, mensaje)
    except OSError as error:
        if cliente is not None:
            print(f"Conexión de {cliente.apodo} cerrada: {error}")
    finally:
        _desconectar(conexion)


def iniciar_servidor(host: str = HOST, port: int = PORT) -> None:
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        servidor.bind((host, port))
        servidor.listen()
        print(f"Servidor de chat escuchando en {host}:{port}.")

        while True:
            conexion, direccion = servidor.accept()
            print(f"Conexión entrante desde {direccion[0]}:{direccion[1]}.")
            hilo = threading.Thread(
                target=_atender_cliente,
                args=(conexion,),
                daemon=True,
            )
            hilo.start()
    except KeyboardInterrupt:
        print("\nCerrando el servidor.")
    finally:
        servidor.close()


if __name__ == "__main__":
    iniciar_servidor()
