"""
Este módulo gestiona las relaciones entre los nodos en la base de datos.
Los IDs aquí son ENTEROS de la base de datos; la traducción a 'cli-1'
la realiza el módulo formato.py.
Cada cambio se anota en el historial dentro de la misma transacción
con 'with conn:' para que si algo falla no quede nada a medias.

Tareas: T17 (relacionar, desrelacionar, vecinos) y T22b (relacionar/desrelacionar
registran en el historial de los dos nodos, en la misma transacción).
"""
from historial import registrar


def _foto(origen, destino, tipo):
    """
    Convierte los datos de una relación en un diccionario para el historial.

    Args:
        origen (int): ID del nodo de origen.
        destino (int): ID del nodo de destino.
        tipo (str): Tipo de relación.

    Returns:
        dict: Diccionario con la estructura necesaria para el historial.
    """
    return {"sourceId": str(origen), "targetId": str(destino), "type": tipo}


def relacionar(conn, origen, destino, tipo, usuario_id):
    """
    Une dos nodos mediante una relación.

    Args:
        conn (sqlite3.Connection): Conexión a la base de datos.
        origen (int): ID del nodo de origen.
        destino (int): ID del nodo de destino.
        tipo (str): Tipo de relación.
        usuario_id (int): ID del usuario que crea la relación.

    Returns:
        int: El ID de la nueva relación.

    Raises:
        sqlite3.IntegrityError: Si se intenta crear un duplicado o un lazo (controlado por el esquema).
    """
    with conn:
        cur = conn.execute(
            "INSERT INTO relaciones (origen_id, destino_id, tipo) VALUES (?, ?, ?)", (origen, destino, tipo)
        )
        foto = _foto(origen, destino, tipo)
        # una relación cambia dos nodos: se anota en el historial de cada uno
        registrar(conn, origen, usuario_id, "relacionar", None, foto)
        registrar(conn, destino, usuario_id, "relacionar", None, foto)
    return cur.lastrowid


def desrelacionar(conn, origen, destino, tipo, usuario_id):
    """
    Borra una relación existente (el borrado en la tabla relaciones es real).

    Args:
        conn (sqlite3.Connection): Conexión a la base de datos.
        origen (int): ID del nodo de origen.
        destino (int): ID del nodo de destino.
        tipo (str): Tipo de relación a borrar.
        usuario_id (int): ID del usuario que realiza la eliminación.

    Returns:
        bool: True si la relación existía y fue borrada, False de lo contrario.

    Raises:
        sqlite3.IntegrityError: Si hay un error de integridad en la base de datos.
    """
    with conn:
        cur = conn.execute(
            "DELETE FROM relaciones WHERE origen_id = ? AND destino_id = ? AND tipo = ?",
            (origen, destino, tipo),
        )
        if cur.rowcount == 0:
            return False
        foto = _foto(origen, destino, tipo)
        registrar(conn, origen, usuario_id, "desrelacionar", foto, None)
        registrar(conn, destino, usuario_id, "desrelacionar", foto, None)
    return True


def vecinos(conn, nodo_id):
    """
    Obtiene los nodos unidos a un nodo_id, tanto como origen como destino.

    Args:
        conn (sqlite3.Connection): Conexión a la base de datos.
        nodo_id (int): ID del nodo para buscar sus vecinos.

    Returns:
        list: Lista de tuplas con los vecinos (vecino_id, título, tipo).
    """
    return conn.execute(
        """
        SELECT r.destino_id AS vecino_id, v.titulo, r.tipo
        FROM relaciones r JOIN nodos v ON v.id = r.destino_id
        WHERE r.origen_id = ? AND v.borrado = 0
        UNION
        SELECT r.origen_id, v.titulo, r.tipo
        FROM relaciones r JOIN nodos v ON v.id = r.origen_id
        WHERE r.destino_id = ? AND v.borrado = 0
        ORDER BY vecino_id
        """,
        (nodo_id, nodo_id),
    ).fetchall()

# ---------------------------------------------------------------------------
# Generación automática de relaciones al importar archivos
import json
import re
import unicodedata


def _normalizar_clave(texto):
    """Normaliza encabezados para comparar 'ID Cliente', 'id_cliente', etc."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", texto.lower())


def _normalizar_valor(valor):
    """Normaliza valores de referencia sin distinguir mayúsculas ni espacios externos."""
    if valor is None:
        return ""
    return str(valor).strip().casefold()


_REFERENCIAS = {
    "Cliente": {
        "cliente", "idcliente", "clienteid", "iddelcliente", "clienteidexterno",
        "codigocliente", "codcliente", "nombrecliente", "cliente nombre",
        "razonsocial", "emailcliente", "correocliente", "mailcliente",
        "telefonocliente",
    },
    "Producto": {
        "producto", "idproducto", "productoid", "iddelproducto",
        "codigoproducto", "codproducto", "nombreproducto", "sku",
    },
    "Pedido": {
        "pedido", "idpedido", "pedidoid", "iddelpedido", "numeropedido",
        "codigopedido", "nombrepedido",
    },
}

_IDENTIFICADORES = {
    "Cliente": {
        "id", "idcliente", "clienteid", "codigocliente", "codcliente",
        "codigo", "code", "uuid", "externalid", "externalkey",
        "cliente", "nombre", "name", "nombrecliente", "razonsocial",
        "email", "emailcliente", "correo", "correoelectronico",
        "correocliente", "mail", "telefono", "telefonocliente",
    },
    "Producto": {
        "id", "idproducto", "productoid", "codigoproducto", "codproducto",
        "codigo", "code", "uuid", "externalid", "externalkey", "sku",
        "producto", "nombre", "name", "nombreproducto",
    },
    "Pedido": {
        "id", "idpedido", "pedidoid", "numeropedido", "codigopedido",
        "codigo", "code", "uuid", "externalid", "externalkey",
        "pedido", "nombre", "name", "nombrepedido", "numero",
    },
}


def _tipo_referenciado(clave):
    """Identifica si una columna representa una referencia a Cliente/Producto/Pedido."""
    clave = _normalizar_clave(clave)

    for tipo, alias in _REFERENCIAS.items():
        if clave in {_normalizar_clave(a) for a in alias}:
            return tipo

    # Acepta variantes como id_del_cliente, cliente_codigo o nombre_de_producto,
    # sin interpretar columnas como total_pedido o fecha_pedido como referencias.
    if "cliente" in clave and any(
        palabra in clave for palabra in ("id", "codigo", "cod", "nombre", "email", "correo", "mail", "telefono")
    ):
        return "Cliente"
    if "producto" in clave and any(
        palabra in clave for palabra in ("id", "codigo", "cod", "nombre", "sku")
    ):
        return "Producto"
    if "pedido" in clave and any(
        palabra in clave for palabra in ("id", "codigo", "cod", "numero", "nombre")
    ):
        return "Pedido"
    return None


def _valores_identificadores(fila, tipo):
    """Devuelve valores con los que otras filas pueden referenciar esta entidad."""
    valores = {_normalizar_valor(fila["titulo"])}
    try:
        datos = json.loads(fila["contenido"] or "{}")
    except (TypeError, json.JSONDecodeError):
        datos = {}

    claves_validas = _IDENTIFICADORES[tipo]
    for clave, valor in datos.items():
        if _normalizar_clave(clave) in claves_validas:
            normalizado = _normalizar_valor(valor)
            if normalizado:
                valores.add(normalizado)
    valores.discard("")
    return valores


def _orientar_relacion(origen_id, origen_tipo, destino_id, destino_tipo):
    """Aplica la orientación y el nombre habitual de las relaciones del ERP."""
    tipos = {origen_tipo, destino_tipo}

    if tipos == {"Pedido", "Cliente"}:
        pedido_id = origen_id if origen_tipo == "Pedido" else destino_id
        cliente_id = destino_id if origen_tipo == "Pedido" else origen_id
        return pedido_id, cliente_id, "pertenece a"

    if tipos == {"Pedido", "Producto"}:
        pedido_id = origen_id if origen_tipo == "Pedido" else destino_id
        producto_id = destino_id if origen_tipo == "Pedido" else origen_id
        return pedido_id, producto_id, "contiene"

    return origen_id, destino_id, "relacionado con"


def generar_relaciones_automaticas(conn, nodos_nuevos, usuario_id):
    """
    Crea relaciones usando columnas que referencian otra entidad (por ejemplo
    id_cliente, SKU o nombre_producto).

    Se revisan todos los nodos activos cada vez que se importa un archivo. Así
    también se resuelven referencias pendientes si primero se importó un pedido
    y recién después el cliente o producto al que apunta.

    Solo crea una relación cuando la referencia coincide con un único nodo activo.
    Así evita inventar enlaces cuando existen identificadores ambiguos.

    Args:
        conn: conexión SQLite.
        nodos_nuevos: IDs internos de los nodos recién creados.
        usuario_id: usuario que realiza la importación.

    Returns:
        int: cantidad de relaciones nuevas.
    """
    ids_nuevos = {int(nodo_id) for nodo_id in nodos_nuevos}
    if not ids_nuevos:
        return 0

    filas = conn.execute(
        """
        SELECT n.id, t.nombre AS tipo, n.titulo, n.contenido
        FROM nodos n
        JOIN tipos_nodo t ON t.id = n.tipo_id
        WHERE n.borrado = 0
        ORDER BY n.id
        """
    ).fetchall()

    por_tipo_y_valor = {}
    por_id = {}
    for fila in filas:
        por_id[fila["id"]] = fila
        for valor in _valores_identificadores(fila, fila["tipo"]):
            por_tipo_y_valor.setdefault((fila["tipo"], valor), set()).add(fila["id"])

    creadas = 0
    procesadas = set()

    # Recorremos todos los nodos activos, no solo los recién importados:
    # una entidad que llega ahora puede completar la referencia de un pedido anterior.
    for nodo_id, origen in por_id.items():

        try:
            datos = json.loads(origen["contenido"] or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(datos, dict):
            continue

        for clave, valor in datos.items():
            tipo_destino = _tipo_referenciado(clave)
            valor_ref = _normalizar_valor(valor)
            if (
                tipo_destino is None
                or tipo_destino == origen["tipo"]
                or not valor_ref
            ):
                continue

            candidatos = por_tipo_y_valor.get((tipo_destino, valor_ref), set())
            # Si no hay coincidencia o hay varias, no inventamos una relación.
            if len(candidatos) != 1:
                continue

            destino_id = next(iter(candidatos))
            if destino_id == nodo_id:
                continue

            fila_destino = por_id[destino_id]
            origen_rel, destino_rel, tipo_rel = _orientar_relacion(
                nodo_id, origen["tipo"], destino_id, fila_destino["tipo"]
            )
            clave_relacion = (origen_rel, destino_rel, tipo_rel)
            if clave_relacion in procesadas:
                continue
            procesadas.add(clave_relacion)

            existe = conn.execute(
                """
                SELECT 1 FROM relaciones
                WHERE origen_id = ? AND destino_id = ? AND tipo = ?
                """,
                clave_relacion,
            ).fetchone()
            if existe:
                continue

            relacionar(
                conn,
                origen_rel,
                destino_rel,
                tipo_rel,
                usuario_id,
            )
            creadas += 1

    return creadas

