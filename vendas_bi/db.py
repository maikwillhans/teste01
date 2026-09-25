"""Conexão com a base SQLite."""

import os
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
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    return conn
