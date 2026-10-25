import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import crear_app  # noqa: E402


def test_importa_fuente_en_base_persistente_sin_usuarios(tmp_path):
    ruta_db = tmp_path / "import.db"
    app = crear_app(str(ruta_db))
    with sqlite3.connect(ruta_db) as conn:
        conn.executemany(
            "INSERT INTO tipos_nodo (nombre) VALUES (?)",
            [("Cliente",), ("Producto",), ("Pedido",)],
        )

    response = app.test_client().post(
        "/api/sources/import",
        json={
            "fileName": "clientes.xlsx",
            "columns": ["id_cliente", "nombre_cliente"],
            "rows": [["C001", "Ana"]],
            "sourceType": "Excel / CSV",
        },
    )

    assert response.status_code == 201
    assert response.get_json()["imported"] == 1
    with sqlite3.connect(ruta_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM historial").fetchone()[0] == 0
