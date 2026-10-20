"""Pruebas de la generación automática de relaciones durante la importación."""
import json

from db import conectar, crear_esquema
from relaciones import generar_relaciones_automaticas


def _preparar_base():
    conn = conectar(":memory:")
    crear_esquema(conn)

    with conn:
        for nombre in ("Cliente", "Producto", "Pedido"):
            conn.execute("INSERT INTO tipos_nodo (nombre) VALUES (?)", (nombre,))
        conn.execute(
            "INSERT INTO fuentes (nombre, tipo, estado) VALUES ('prueba.xlsx', 'Excel', 'ok')"
        )
        conn.execute(
            """
            INSERT INTO usuarios (id, email, nombre, hash_clave, rol)
            VALUES (1, 'prueba@local', 'Prueba', 'hash', 'admin')
            """
        )
    return conn


def _nodo(conn, tipo, titulo, contenido):
    tipo_id = conn.execute(
        "SELECT id FROM tipos_nodo WHERE nombre = ?", (tipo,)
    ).fetchone()["id"]
    fuente_id = conn.execute(
        "SELECT id FROM fuentes WHERE nombre = 'prueba.xlsx'"
    ).fetchone()["id"]
    cur = conn.execute(
        """
        INSERT INTO nodos (tipo_id, fuente_id, creado_por, titulo, contenido)
        VALUES (?, ?, 1, ?, ?)
        """,
        (tipo_id, fuente_id, titulo, json.dumps(contenido, ensure_ascii=False)),
    )
    return cur.lastrowid


def test_generar_relaciones_automaticas_desde_claves_foraneas():
    conn = _preparar_base()
    try:
        cliente_id = _nodo(
            conn, "Cliente", "Ana Pérez",
            {"id_cliente": "CLI-01", "nombre": "Ana Pérez"},
        )
        producto_id = _nodo(
            conn, "Producto", "Malbec 750 ml",
            {"sku": "SKU-01", "nombre_producto": "Malbec 750 ml"},
        )
        pedido_id = _nodo(
            conn, "Pedido", "PED-100",
            {
                "id_pedido": "PED-100",
                "id_cliente": "cli-01",
                "id_producto": "sku-01",
                "total": 12500,
            },
        )

        creadas = generar_relaciones_automaticas(conn, [pedido_id], 1)

        relaciones = conn.execute(
            """
            SELECT origen_id, destino_id, tipo
            FROM relaciones
            ORDER BY tipo
            """
        ).fetchall()

        assert creadas == 2
        assert {
            (r["origen_id"], r["destino_id"], r["tipo"])
            for r in relaciones
        } == {
            (pedido_id, cliente_id, "pertenece a"),
            (pedido_id, producto_id, "contiene"),
        }

        # Volver a procesar el mismo nodo no duplica relaciones.
        assert generar_relaciones_automaticas(conn, [pedido_id], 1) == 0
        assert conn.execute("SELECT COUNT(*) FROM relaciones").fetchone()[0] == 2
    finally:
        conn.close()


def test_no_crea_relacion_si_la_referencia_es_ambigua():
    conn = _preparar_base()
    try:
        _nodo(conn, "Cliente", "Cliente uno", {"id_cliente": "C-1"})
        _nodo(conn, "Cliente", "Cliente duplicado", {"id_cliente": "C-1"})
        pedido_id = _nodo(
            conn, "Pedido", "PED-200",
            {"id_pedido": "PED-200", "id_cliente": "C-1"},
        )

        assert generar_relaciones_automaticas(conn, [pedido_id], 1) == 0
        assert conn.execute("SELECT COUNT(*) FROM relaciones").fetchone()[0] == 0
    finally:
        conn.close()


def test_detecta_referencias_por_nombre_de_entidad():
    conn = _preparar_base()
    try:
        cliente_id = _nodo(conn, "Cliente", "Ana Pérez", {"nombre": "Ana Pérez"})
        pedido_id = _nodo(
            conn, "Pedido", "PED-300",
            {"id_pedido": "PED-300", "cliente": "Ana Pérez"},
        )

        assert generar_relaciones_automaticas(conn, [pedido_id], 1) == 1
        relacion = conn.execute(
            "SELECT origen_id, destino_id, tipo FROM relaciones"
        ).fetchone()
        assert (relacion["origen_id"], relacion["destino_id"], relacion["tipo"]) == (
            pedido_id, cliente_id, "pertenece a"
        )
    finally:
        conn.close()



def test_resuelve_referencias_cuando_el_cliente_se_importa_despues_del_pedido():
    conn = _preparar_base()
    try:
        pedido_id = _nodo(
            conn, "Pedido", "PED-400",
            {"id_pedido": "PED-400", "id_cliente": "C-400"},
        )
        assert generar_relaciones_automaticas(conn, [pedido_id], 1) == 0

        cliente_id = _nodo(
            conn, "Cliente", "Cliente cuatro",
            {"id_cliente": "C-400"},
        )
        assert generar_relaciones_automaticas(conn, [cliente_id], 1) == 1

        relacion = conn.execute(
            "SELECT origen_id, destino_id, tipo FROM relaciones"
        ).fetchone()
        assert (relacion["origen_id"], relacion["destino_id"], relacion["tipo"]) == (
            pedido_id, cliente_id, "pertenece a"
        )
    finally:
        conn.close()
