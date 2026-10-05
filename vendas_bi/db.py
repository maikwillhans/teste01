"""Conexão com a base SQLite."""

import os
import re
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BANCO_PADRAO = Path(os.environ.get("VENDAS_BI_DB", RAIZ / "data" / "sistema.db"))
SCHEMA = Path(__file__).with_name("schema.sql")


def conectar(caminho: str | Path | None = None) -> sqlite3.Connection:
    """Abre (e cria, se preciso) a base e garante o schema atualizado."""
    caminho = Path(caminho or BANCO_PADRAO)
    if str(caminho) != ":memory:":
        caminho.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(caminho, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    schema = SCHEMA.read_text(encoding="utf-8")
    conn.executescript(schema)
    _migrar(conn, schema)
    return conn


def _migrar(conn: sqlite3.Connection, schema: str) -> None:
    """Atualiza bases criadas por versões anteriores do sistema."""
    sql_carga = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'carga'").fetchone()[0]
    if "'pedidos'" not in sql_carga:
        # a restrição de tipos da tabela carga ganhou 'pedidos': recria a tabela mantendo os dados
        ddl = re.search(r"CREATE TABLE IF NOT EXISTS carga \(.*?\n\);", schema, re.S).group(0)
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.executescript(
            "BEGIN;"
            + ddl.replace("IF NOT EXISTS carga", "carga_nova")
            + "INSERT INTO carga_nova SELECT * FROM carga;"
              "DROP TABLE carga;"
              "ALTER TABLE carga_nova RENAME TO carga;"
              "COMMIT;")
        conn.execute("PRAGMA foreign_keys = ON")
