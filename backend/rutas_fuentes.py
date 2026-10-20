"""T28 - GET /api/sources

Devuelve las fuentes como las muestra el front:
    [{id, name, type, status, lastSync, recordCount}, ...]

recordCount no se guarda: se calcula contando los nodos de cada fuente,
sin contar los borrados (borrado = 1).
"""
from flask import Blueprint, g, jsonify, request
from datetime import datetime
import math
import re
import unicodedata
import sqlite3

from historial import registrar
from nodos import _tipo_id
from relaciones import generar_relaciones_automaticas
bp = Blueprint("fuentes", __name__)
# El filtro de borrados va en el ON y no en un WHERE: asi una fuente sin nodos
# (o con todos borrados) sigue apareciendo, con recordCount = 0.
SELECT_FUENTES = """
    SELECT f.id, f.nombre, f.tipo, f.estado, f.ultima_sync,
           COUNT(n.id) AS cantidad
    FROM fuentes f
    LEFT JOIN nodos n ON n.fuente_id = f.id AND n.borrado = 0
    GROUP BY f.id
    ORDER BY f.id
"""


def _a_source(fila):
    ultima_sync = fila["ultima_sync"]

    if ultima_sync:
        try:
            ultima_sync = datetime.fromisoformat(
                ultima_sync
            ).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            pass
    else:
        ultima_sync = ""

    return {
        "id": fila["id"],
        "name": fila["nombre"],
        "type": fila["tipo"],
        "status": fila["estado"],
        "lastSync": ultima_sync,
        "recordCount": fila["cantidad"],
    }

@bp.route("/api/sources", methods=["GET"])
def listar_fuentes():
    return jsonify([_a_source(f) for f in g.conn.execute(SELECT_FUENTES).fetchall()])
from rutas_auth import requiere_login


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", texto.lower())


def _detectar_tipo(columnas):
    """Detecta el tipo principal de las filas, distinguiéndolo de sus claves foráneas."""
    encabezados = {_normalizar(c) for c in columnas}

    # Un identificador propio de pedido tiene prioridad sobre id_cliente/id_producto,
    # porque esas columnas suelen ser referencias dentro de una tabla de pedidos.
    claves_pedido = {
        "idpedido", "pedidoid", "numeropedido", "codigopedido"
    }
    if encabezados & claves_pedido:
        tipo = "Pedido"
    else:
        marcadores_cliente = {
            "idcliente", "clienteid", "codigocliente", "codcliente",
            "nombrecliente", "razonsocial", "emailcliente", "correocliente",
        }
        marcadores_producto = {
            "idproducto", "productoid", "codigoproducto", "codproducto",
            "nombreproducto", "sku",
        }

        tiene_cliente = bool(encabezados & marcadores_cliente)
        tiene_producto = bool(encabezados & marcadores_producto)

        # Una tabla con ID propio, referencias a cliente y producto y columnas
        # de fecha/importe suele ser una tabla de pedidos aunque use solo "id".
        if (
            "id" in encabezados
            and bool(encabezados & {"idcliente", "clienteid", "cliente"})
            and bool(encabezados & {"idproducto", "productoid", "producto", "sku"})
            and bool(encabezados & {"fecha", "total", "importe", "estado"})
        ):
            tipo = "Pedido"
        # Nombre de la entidad + sus atributos suelen identificar mejor el archivo
        # que una columna id_cliente/id_producto que podría ser una referencia.
        elif "nombreproducto" in encabezados or (
            "sku" in encabezados and ("precio" in encabezados or "stock" in encabezados)
        ):
            tipo = "Producto"
        elif "nombrecliente" in encabezados or "razonsocial" in encabezados:
            tipo = "Cliente"
        elif tiene_producto and not tiene_cliente:
            tipo = "Producto"
        elif tiene_cliente and not tiene_producto:
            tipo = "Cliente"
        else:
            patrones = {
                "Cliente": {
                    "idcliente", "clienteid", "nombrecliente",
                    "razonsocial", "emailcliente", "correocliente",
                    "telefonocliente",
                },
                "Producto": {
                    "idproducto", "productoid", "nombreproducto",
                    "codigoproducto", "sku", "precio", "stock",
                },
                "Pedido": {
                    "numeropedido", "codigopedido", "fechapedido",
                    "totalpedido", "estadopedido",
                },
            }
            puntajes = {
                entidad: len(encabezados & patron)
                for entidad, patron in patrones.items()
            }
            mejor = max(puntajes.values(), default=0)
            ganadores = [
                entidad for entidad, puntaje in puntajes.items()
                if puntaje == mejor and puntaje > 0
            ]
            if len(ganadores) != 1:
                raise ValueError(
                    "No se pudo determinar el tipo de entidad con seguridad. "
                    "Revisá los encabezados del archivo."
                )
            tipo = ganadores[0]

    columnas_nombre = {
        "Cliente": [
            "razonsocial", "nombrecliente", "cliente", "nombre", "idcliente",
            "clienteid", "codigocliente", "id"
        ],
        "Producto": [
            "nombreproducto", "producto", "nombre", "sku", "idproducto",
            "productoid", "codigoproducto", "id"
        ],
        "Pedido": [
            "numeropedido", "codigopedido", "idpedido",
            "pedido", "nombrepedido", "id"
        ],
    }

    mapa = {_normalizar(c): c for c in columnas}
    columna_nombre = next(
        (mapa[c] for c in columnas_nombre[tipo] if c in mapa),
        None,
    )

    # Para pedidos, si solo hay id_pedido y no una columna de nombre,
    # el identificador funciona como título del nodo.
    if columna_nombre is None:
        if tipo == "Pedido":
            columna_nombre = next(
                (mapa[c] for c in ("numeropedido", "codigopedido", "idpedido", "pedidoid", "id") if c in mapa),
                None,
            )

    if columna_nombre is None:
        raise ValueError(
            f"Se detectó {tipo}, pero no se encontró una columna "
            "que identifique cada registro."
        )

    return tipo, columna_nombre

@bp.post("/api/sources/import")
@requiere_login
def importar_fuente():
    datos = request.get_json(silent=True)

    if not isinstance(datos, dict):
        return jsonify({"error": "Se esperaba un objeto JSON"}), 400

    nombre = datos.get("fileName")
    columnas = datos.get("columns")
    filas = datos.get("rows")
    tipo_fuente = datos.get("sourceType", "Excel / CSV")

    if not isinstance(nombre, str) or not nombre.strip():
        return jsonify({"error": "Falta el nombre del archivo"}), 400

    if not isinstance(columnas, list) or not columnas:
        return jsonify({"error": "Faltan los encabezados"}), 400

    if not all(isinstance(c, str) and c.strip() for c in columnas):
        return jsonify({"error": "Hay encabezados vacÃ­os o invÃ¡lidos"}), 400

    if len({_normalizar(c) for c in columnas}) != len(columnas):
        return jsonify({
            "error": "Hay encabezados duplicados"
        }), 400

    if not isinstance(filas, list) or not filas:
        return jsonify({"error": "El archivo no contiene registros"}), 400

    if not isinstance(tipo_fuente, str) or not tipo_fuente.strip():
        return jsonify({"error": "El tipo de fuente no es vÃ¡lido"}), 400

    try:
        tipo_entidad, columna_nombre = _detectar_tipo(columnas)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    registros = []

    for indice, fila in enumerate(filas, start=2):
        if not isinstance(fila, list) or len(fila) != len(columnas):
            return jsonify({
                "error": f"La fila {indice} no coincide con los encabezados"
            }), 400

        registro = dict(zip(columnas, fila))

        if not all(
            valor is None or isinstance(valor, (str, int, float))
            and not isinstance(valor, bool)
            and (not isinstance(valor, float) or math.isfinite(valor))
            for valor in registro.values()
        ):
            return jsonify({
                "error": f"La fila {indice} contiene datos invÃ¡lidos"
            }), 400

        titulo = registro.get(columna_nombre)

        if titulo is None or not str(titulo).strip():
            return jsonify({
                "error": f"La fila {indice} no tiene un nombre vÃ¡lido "
                         f"en la columna {columna_nombre}"
            }), 400

        registros.append((str(titulo).strip(), registro))

    conn = g.conn
    nombre = nombre.strip()

    nodo_ids = []

    try:
        with conn:
            existente = conn.execute(
                "SELECT id FROM fuentes WHERE nombre = ?",
                (nombre,),
            ).fetchone()

            if existente:
                return jsonify({
                    "error": f"Ya existe una fuente llamada {nombre}"
                }), 409

            ahora = datetime.now().isoformat(timespec="seconds")

            cursor = conn.execute(
                """
                INSERT INTO fuentes (nombre, tipo, estado, ultima_sync)
                VALUES (?, ?, 'ok', ?)
                """,
                (nombre, tipo_fuente.strip(), ahora),
            )

            fuente_id = cursor.lastrowid
            tipo_id = _tipo_id(conn, tipo_entidad)

            for titulo, registro in registros:
                cursor = conn.execute(
                    """
                    INSERT INTO nodos
                        (tipo_id, fuente_id, creado_por, titulo, contenido)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        tipo_id,
                        fuente_id,
                        g.usuario_id,
                        titulo,
                        __import__("json").dumps(
                            registro, ensure_ascii=False, allow_nan=False
                        ),
                    ),
                )

                nodo_id = cursor.lastrowid
                nodo_ids.append(nodo_id)

                registrar(
                    conn,
                    nodo_id,
                    g.usuario_id,
                    "crear",
                    None,
                    {
                        "name": titulo,
                        "type": tipo_entidad,
                        "source": nombre,
                        "data": registro,
                    },
                )

        # Los nodos ya están guardados. Ahora resolvemos sus referencias contra
        # las entidades existentes y generamos las relaciones que sean inequívocas.
        relaciones_creadas = generar_relaciones_automaticas(
            conn, nodo_ids, g.usuario_id
        )

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "No se pudo importar el archivo por un conflicto de datos"
        }), 409

    return jsonify({
        "sourceId": fuente_id,
        "source": nombre,
        "entityType": tipo_entidad,
        "nameColumn": columna_nombre,
        "imported": len(registros),
        "relationshipsCreated": relaciones_creadas,
    }), 201
