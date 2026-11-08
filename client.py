import socket
import threading


HOST = "127.0.0.1"
PORT = 7000
BUFFER_SIZE = 4096


def _escuchar(
    conexion: socket.socket,
    detener: threading.Event,
) -> None:
    buffer = bytearray()
    try:
        while not detener.is_set():
            datos = conexion.recv(BUFFER_SIZE)
            if not datos:
                print("\nEl servidor cerró la conexión.")
                break
            buffer.extend(datos)

            while b"\n" in buffer:
                linea, _, restante = buffer.partition(b"\n")
                buffer = bytearray(restante)
                mensaje = linea.decode("utf-8", errors="replace").rstrip("\r")
                if mensaje:
                    print(f"\n{mensaje}")
    except OSError as error:
        if not detener.is_set():
            print(f"\nSe perdió la conexión con el servidor: {error}")
    finally:
        detener.set()


def iniciar_cliente() -> None:
    while True:
        apodo = input("Nombre o apodo: ").strip()
        if apodo:
            break
        print("El apodo no puede estar vacío.")

    try:
        conexion = socket.create_connection((HOST, PORT))
    except OSError as error:
        print(f"No se pudo conectar al servidor en {HOST}:{PORT}: {error}")
        return

    detener = threading.Event()
    hilo_recepcion = threading.Thread(
        target=_escuchar,
        args=(conexion, detener),
        name="cliente-recepcion",
        daemon=True,
    )

    try:
        conexion.sendall(f"{apodo}\n".encode("utf-8"))
        hilo_recepcion.start()
        print("Conectado. Escribe /salir para terminar.")

        while not detener.is_set():
            try:
                mensaje = input("> ")
            except EOFError:
                break

            if mensaje.strip() == "/salir":
                break
            if not mensaje:
                continue

            try:
                conexion.sendall(f"{mensaje}\n".encode("utf-8"))
            except OSError as error:
                print(f"No se pudo enviar el mensaje: {error}")
                break
    except (KeyboardInterrupt, OSError) as error:
        if isinstance(error, OSError):
            print(f"No se pudo iniciar la sesión: {error}")
    finally:
        detener.set()
        try:
            conexion.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conexion.close()
        if hilo_recepcion.is_alive():
            hilo_recepcion.join(timeout=1)
        print("Desconectado.")


if __name__ == "__main__":
    iniciar_cliente()
