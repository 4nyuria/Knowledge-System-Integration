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
    """Detecta Cliente, Producto o Pedido usando los encabezados."""
    encabezados = {_normalizar(c) for c in columnas}

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
            "idpedido", "pedidoid", "numeropedido",
            "codigopedido", "fechapedido", "totalpedido",
            "estadopedido",
        },
    }

    puntajes = {
        tipo: len(encabezados & patron)
        for tipo, patron in patrones.items()
    }

    mejor = max(puntajes.values(), default=0)
    ganadores = [
        tipo for tipo, puntaje in puntajes.items()
        if puntaje == mejor and puntaje > 0
    ]

    if len(ganadores) != 1:
        raise ValueError(
            "No se pudo determinar el tipo de entidad con seguridad. "
            "RevisÃ¡ los encabezados del archivo."
        )

    tipo = ganadores[0]

    columnas_nombre = {
        "Cliente": [
            "razonsocial", "nombrecliente", "cliente", "nombre"
        ],
        "Producto": [
            "nombreproducto", "producto", "nombre"
        ],
        "Pedido": [
            "numeropedido", "codigopedido", "idpedido",
            "pedido", "nombrepedido"
        ],
    }

    mapa = {_normalizar(c): c for c in columnas}

    columna_nombre = next(
        (mapa[c] for c in columnas_nombre[tipo] if c in mapa),
        None,
    )

    if columna_nombre is None:
        raise ValueError(
            f"Se detectÃ³ {tipo}, pero no se encontrÃ³ una columna "
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
    }), 201
