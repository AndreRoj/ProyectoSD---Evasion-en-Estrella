"""Servidor TCP central para la simulación Aegis-Star.

Acepta los mensajes JSON de los sensores, conserva la matriz de amenazas,
vigila sus heartbeats y publica eventos estructurados para la interfaz.
Un segundo puerto local permite solicitar detecciones manuales.
"""

import json
import socket
import threading
import time

from config import (
    CONTROL_PORT,
    DURACION_DETECCION,
    HOST,
    MAX_SENSORES,
    PORT,
    SECTORES,
    TIMEOUT_SENSOR,
)

# La GUI reconoce las líneas con este prefijo y las interpreta como JSON.
MARCADOR_EVENTO_INTERFAZ = "@@AEGIS_EVENTO@@"

# Estado compartido entre los hilos del servidor; cada sensor ocupa la
# posición definida para su sector y la nave permanece en el centro ("X").
MATRIZ_AMENAZAS = [
    [0, 0, 0],
    [0, "X", 0],
    [0, 0, 0],
]
ULTIMO_HEARTBEAT = {}
SENSORES_CONECTADOS = {}
DETECCIONES_MANUALES = {}
LOCK_ESTADO = threading.Lock()
PARAR_SERVIDOR = threading.Event()
CONEXIONES = set()
LOCK_CONEXIONES = threading.Lock()
ULTIMA_CLASIFICACION = None


class SectorDuplicadoError(ValueError):
    """Indica que otra conexion ya es propietaria del sector."""


def _clasificar_bajo_lock():
    """Clasifica el nivel de peligro a partir de las detecciones activas.

    Se llama con ``LOCK_ESTADO`` adquirido para que las lecturas de la matriz
    y de las detecciones manuales representen un mismo instante.

    Returns:
        ``"SIN AMENAZAS"`` si no hay detecciones, alerta roja si hay una y
        tránsito seguro si hay más de una, de acuerdo con las reglas del
        proyecto.
    """
    ahora = time.monotonic()
    detecciones = sum(
        MATRIZ_AMENAZAS[fila][columna] == 1 or DETECCIONES_MANUALES.get(sector, 0) > ahora
        for sector, (fila, columna) in SECTORES.items()
    )
    if detecciones == 0:
        return "SIN AMENAZAS"
    if detecciones == 1:
        return "¡ALERTA ROJA DE COLISIÓN INMINENTE!"
    return "TRÁNSITO SEGURO (trayectoria paralela/tangencial sin impacto)"


def _actualizar_clasificacion(detalle=None):
    """Publica la clasificación actual y el estado completo de la matriz.

    La clasificación solo se imprime como texto cuando cambia. En cambio,
    cada llamada emite un evento JSON para que la GUI sincronice imágenes,
    estado de peligro y sensores conectados desde una instantánea común.

    Args:
        detalle: Descripción opcional del cambio que originó la actualización.
    """
    global ULTIMA_CLASIFICACION
    with LOCK_ESTADO:
        clasificacion = _clasificar_bajo_lock()
        if clasificacion != ULTIMA_CLASIFICACION:
            ULTIMA_CLASIFICACION = clasificacion
            print(f"[NAVE] {clasificacion}", flush=True)
            if clasificacion == "¡ALERTA ROJA DE COLISIÓN INMINENTE!":
                print("[NAVE] Maniobra de evasion y escudos activados.", flush=True)
            elif clasificacion.startswith("TRÁNSITO SEGURO"):
                print("[NAVE] ALERTA NO ACTIVADA.", flush=True)

        matriz = [fila[:] for fila in MATRIZ_AMENAZAS]
        ahora = time.monotonic()
        for sector, vencimiento in DETECCIONES_MANUALES.items():
            if vencimiento > ahora:
                fila, columna = SECTORES[sector]
                matriz[fila][columna] = 1

        evento = {
            "tipo": "estado",
            "matriz": matriz,
            "conectados": list(SENSORES_CONECTADOS),
            "clasificacion": clasificacion,
            "peligro": clasificacion == "¡ALERTA ROJA DE COLISIÓN INMINENTE!",
            "detalle": detalle,
        }
        print(
            MARCADOR_EVENTO_INTERFAZ + json.dumps(evento),
            flush=True,
        )


def _procesar_mensaje(mensaje, sector_conexion, conexion):
    """Valida un heartbeat o una detección y actualiza el estado compartido.

    El primer mensaje registra qué sector pertenece a la conexión; los
    posteriores deben identificar ese mismo sector. Un heartbeat actualiza el
    instante del último latido, mientras que una detección modifica la matriz.

    Args:
        mensaje: Objeto JSON decodificado enviado por el sensor.
        sector_conexion: Sector previamente asociado a esta conexión, o
            ``None`` mientras todavía no se ha registrado.
        conexion: Socket propietario del sector.

    Returns:
        El nombre del sector asociado al mensaje.

    Raises:
        ValueError: Si el mensaje o el sector no cumplen el protocolo.
        SectorDuplicadoError: Si otro socket ya es propietario del sector.
    """
    if not isinstance(mensaje, dict):
        raise ValueError("El mensaje debe ser un objeto JSON")
    tipo = mensaje.get("tipo")
    sector = mensaje.get("sector")
    if not isinstance(sector, str) or sector not in SECTORES:
        raise ValueError("Sector ausente o desconocido")
    if sector_conexion and sector != sector_conexion:
        raise ValueError("Sector ausente, desconocido o distinto al registrado")

    estado = None
    if tipo == "DETECCION":
        estado = mensaje.get("estado")
        if type(estado) is not int or estado not in (0, 1):
            raise ValueError("El estado de deteccion debe ser 0 o 1")
    elif tipo != "HEARTBEAT":
        raise ValueError(f"Tipo de mensaje no soportado: {tipo!r}")

    with LOCK_ESTADO:
        propietario = SENSORES_CONECTADOS.get(sector)
        if propietario is not None and propietario is not conexion:
            raise SectorDuplicadoError(f"El sector {sector} ya tiene una conexion activa")
        if propietario is None:
            SENSORES_CONECTADOS[sector] = conexion
        ULTIMO_HEARTBEAT[sector] = time.monotonic()
        if estado is not None:
            fila, columna = SECTORES[sector]
            MATRIZ_AMENAZAS[fila][columna] = estado
        else:
            print(
                MARCADOR_EVENTO_INTERFAZ
                + json.dumps(
                    {"tipo": "heartbeat", "sector": sector},
                ),
                flush=True,
            )

    if estado is not None:
        print(f"[NAVE] Sector {sector}: deteccion={estado}.", flush=True)
        _actualizar_clasificacion(f"Sector {sector}: detección={estado}.")
    return sector


def _simular_deteccion(sector):
    """Activa una detección manual temporal en un sector conectado.

    Args:
        sector: Nombre del sector donde se desea simular el objeto.

    Returns:
        Par ``(éxito, mensaje)`` que describe el resultado de la solicitud.
    """
    if not isinstance(sector, str) or sector not in SECTORES:
        return False, "Sector ausente o desconocido"

    with LOCK_ESTADO:
        if sector not in SENSORES_CONECTADOS:
            return False, f"No hay un sensor conectado en el sector {sector}"
        DETECCIONES_MANUALES[sector] = time.monotonic() + DURACION_DETECCION

    print(f"[NAVE] Sector {sector}: deteccion manual=1.", flush=True)
    _actualizar_clasificacion(f"Detección manual en el sector {sector}.")
    return True, f"Deteccion simulada en el sector {sector}"


def _atender_controles_manual(servidor_control):
    """Atiende solicitudes de detección manual y elimina las que expiran.

    Lee una solicitud JSON por conexión en el puerto de control. En cada ciclo
    también revisa las fechas de expiración de las detecciones manuales y
    publica el nuevo estado si alguna terminó.

    Args:
        servidor_control: Socket de escucha del puerto de control local.
    """
    while not PARAR_SERVIDOR.is_set():
        try:
            conexion, _ = servidor_control.accept()
        except socket.timeout:
            conexion = None
        except OSError:
            if PARAR_SERVIDOR.is_set():
                return
            raise

        if conexion is not None:
            with conexion:
                try:
                    conexion.settimeout(2.0)
                    datos = b""
                    while b"\n" not in datos and len(datos) <= 1024:
                        bloque = conexion.recv(1024)
                        if not bloque:
                            break
                        datos += bloque
                    mensaje = json.loads(datos.split(b"\n", 1)[0].decode("utf-8"))
                    if not isinstance(mensaje, dict) or mensaje.get("tipo") != "SIMULAR_DETECCION":
                        respuesta = {"ok": False, "mensaje": "Solicitud de control no valida"}
                    else:
                        ok, texto = _simular_deteccion(mensaje.get("sector"))
                        respuesta = {"ok": ok, "mensaje": texto}
                except (json.JSONDecodeError, UnicodeDecodeError, ValueError, OSError) as error:
                    respuesta = {"ok": False, "mensaje": f"No se pudo procesar la solicitud: {error}"}
                try:
                    conexion.sendall((json.dumps(respuesta) + "\n").encode("utf-8"))
                except OSError:
                    pass

        ahora = time.monotonic()
        with LOCK_ESTADO:
            expirados = [
                sector
                for sector, vencimiento in DETECCIONES_MANUALES.items()
                if vencimiento <= ahora
            ]
            for sector in expirados:
                DETECCIONES_MANUALES.pop(sector, None)

        if expirados:
            for sector in expirados:
                print(f"[NAVE] Sector {sector}: deteccion manual=0.", flush=True)
            _actualizar_clasificacion(
                "Detección manual finalizada en: " + ", ".join(expirados) + "."
            )


def _atender_sensor(conexion, direccion):
    """Procesa los mensajes de una conexión sensor hasta que se cierre.

    Cada línea debe contener un objeto JSON del protocolo. Si la conexión se
    interrumpe o se rechaza, libera el sector, limpia su detección y retira el
    socket del conjunto global de conexiones.

    Args:
        conexion: Socket TCP aceptado por el servidor principal.
        direccion: Dirección de red del cliente, usada para los diagnósticos.
    """
    sector_conexion = None
    print(f"[NAVE] Conexion recibida desde {direccion}.", flush=True)
    try:
        with conexion, conexion.makefile("r", encoding="utf-8") as lector:
            for linea in lector:
                try:
                    mensaje = json.loads(linea)
                    sector = _procesar_mensaje(mensaje, sector_conexion, conexion)
                except SectorDuplicadoError as error:
                    print(f"[NAVE] Conexion rechazada: {error}.", flush=True)
                    break
                except (json.JSONDecodeError, ValueError) as error:
                    print(f"[NAVE] Mensaje rechazado desde {direccion}: {error}.", flush=True)
                    continue

                if sector_conexion is None:
                    sector_conexion = sector
                    print(f"[NAVE] Sensor {sector} registrado.", flush=True)
    except (ConnectionError, OSError) as error:
        if not PARAR_SERVIDOR.is_set():
            print(f"[NAVE] Error de conexion {direccion}: {error}.", flush=True)
    finally:
        if sector_conexion is not None:
            with LOCK_ESTADO:
                if SENSORES_CONECTADOS.get(sector_conexion) is conexion:
                    SENSORES_CONECTADOS.pop(sector_conexion, None)
                    ULTIMO_HEARTBEAT.pop(sector_conexion, None)
                    fila, columna = SECTORES[sector_conexion]
                    cambio = MATRIZ_AMENAZAS[fila][columna] != 0
                    MATRIZ_AMENAZAS[fila][columna] = 0
                else:
                    cambio = False
            if cambio:
                print(f"[NAVE] Sensor {sector_conexion} desconectado; estado reiniciado.", flush=True)
                _actualizar_clasificacion(
                    f"Sensor {sector_conexion} desconectado; estado reiniciado."
                )
            else:
                print(f"[NAVE] Sensor {sector_conexion} desconectado.", flush=True)
                _actualizar_clasificacion(
                    f"Sensor {sector_conexion} desconectado."
                )
        with LOCK_CONEXIONES:
            CONEXIONES.discard(conexion)


def _monitorear_heartbeats():
    """Desconecta sensores cuyo último heartbeat superó el tiempo límite.

    Comprueba periódicamente las marcas de tiempo con un reloj monotónico.
    Cuando un sensor excede ``TIMEOUT_SENSOR``, borra su estado, actualiza la
    interfaz y cierra su socket.
    """
    while not PARAR_SERVIDOR.wait(0.5):
        ahora = time.monotonic()
        fallos = []
        with LOCK_ESTADO:
            for sector, ultimo in tuple(ULTIMO_HEARTBEAT.items()):
                if ahora - ultimo > TIMEOUT_SENSOR:
                    ULTIMO_HEARTBEAT.pop(sector, None)
                    conexion = SENSORES_CONECTADOS.pop(sector, None)
                    fila, columna = SECTORES[sector]
                    MATRIZ_AMENAZAS[fila][columna] = 0
                    fallos.append((sector, conexion))

        for sector, conexion in fallos:
            print(f"[NAVE] FALLO: sensor {sector} sin heartbeat; marcado desconectado.", flush=True)
            _actualizar_clasificacion(
                f"FALLO: sensor {sector} sin heartbeat; marcado desconectado."
            )
            if conexion is not None:
                try:
                    conexion.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                conexion.close()


def iniciar_servidor():
    """Inicia los sockets y los hilos que componen el servidor central.

    Mantiene un listener para los sensores y otro para controles manuales.
    Cada conexión de sensor se procesa en su propio hilo; al cerrar el
    servidor, se detienen los monitores y se cierran las conexiones activas.
    """
    monitor = threading.Thread(target=_monitorear_heartbeats, name="monitor-heartbeats", daemon=True)
    control = None
    servidor_control = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor_control.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        # El puerto de control acepta solicitudes manuales de la aplicación.
        servidor_control.bind((HOST, CONTROL_PORT))
        servidor_control.listen()
        servidor_control.settimeout(0.5)
        control = threading.Thread(
            target=_atender_controles_manual,
            args=(servidor_control,),
            name="control-manual",
            daemon=True,
        )
        control.start()
        monitor.start()
        # El socket principal recibe heartbeats y detecciones de los sensores.
        servidor.bind((HOST, PORT))
        servidor.listen(MAX_SENSORES)
        servidor.settimeout(0.5)
        print(f"[NAVE] Escuchando en {HOST}:{PORT}.", flush=True)
        _actualizar_clasificacion("Servidor iniciado.")

        while not PARAR_SERVIDOR.is_set():
            try:
                conexion, direccion = servidor.accept()
            except socket.timeout:
                continue

            with LOCK_CONEXIONES:
                if len(CONEXIONES) >= MAX_SENSORES:
                    conexion.close()
                    print("[NAVE] Limite de sensores alcanzado; conexion rechazada.", flush=True)
                    continue
                CONEXIONES.add(conexion)

            hilo = threading.Thread(
                target=_atender_sensor,
                args=(conexion, direccion),
                name=f"sensor-{direccion[0]}:{direccion[1]}",
                daemon=True,
            )
            hilo.start()
    except KeyboardInterrupt:
        print("\n[NAVE] Cerrando servidor...", flush=True)
    finally:
        PARAR_SERVIDOR.set()
        servidor.close()
        servidor_control.close()
        with LOCK_CONEXIONES:
            conexiones = tuple(CONEXIONES)
        for conexion in conexiones:
            try:
                conexion.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            conexion.close()
        monitor.join(timeout=1.0)
        if control is not None:
            control.join(timeout=1.0)


if __name__ == "__main__":
    iniciar_servidor()