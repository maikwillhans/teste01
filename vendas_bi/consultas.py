"""Consultas analíticas usadas pelo dashboard.

Regra de "realizado": vendas (V) menos devoluções (D). Bonificação (B) é
mostrada à parte e não conta para a meta — é a regra que reproduz o "Vendido"
do Resumo Geral das Metas. O realizado da meta é calculado das notas
(view vw_meta), por região + vendedor + produto.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

import pandas as pd


@dataclass
class Filtro:
    periodo: str
    gerentes: list[str] | None = None
    supervisores: list[str] | None = None
    vendedores: list[str] | None = None

    def where(self, alias: str = "") -> tuple[str, list]:
        p = f"{alias}." if alias else ""
        sql, args = [f"{p}periodo = ?"], [self.periodo]
        for col, valores in (("gerente", self.gerentes), ("supervisor", self.supervisores),
                             ("vendedor", self.vendedores)):
            if valores:
                sql.append(f"{p}{col} IN ({','.join('?' * len(valores))})")
                args += valores
        return " AND ".join(sql), args


def _df(conn: sqlite3.Connection, sql: str, args=()) -> pd.DataFrame:
    return pd.read_sql_query(sql, conn, params=list(args))


def periodos(conn) -> list[str]:
    sql = "SELECT periodo FROM vw_venda UNION SELECT periodo FROM meta ORDER BY 1 DESC"
    return [r[0] for r in conn.execute(sql)]


def opcoes(conn, periodo: str) -> dict[str, list[str]]:
    out = {}
    for col in ("gerente", "supervisor", "vendedor"):
        sql = (f"SELECT {col} FROM vw_venda WHERE periodo = ? UNION "
               f"SELECT {col} FROM vw_meta WHERE periodo = ? ORDER BY 1")
        out[col] = [r[0] for r in conn.execute(sql, (periodo, periodo)) if r[0]]
    return out


REALIZADO = "operacao IN ('V','D')"


def indicadores(conn, f: Filtro) -> dict:
    w, a = f.where()
    v = conn.execute(
        f"""SELECT
              COALESCE(SUM(CASE WHEN {REALIZADO} THEN vlrtot END), 0),
              COALESCE(SUM(CASE WHEN {REALIZADO} THEN qtd_kg END), 0),
              COALESCE(SUM(CASE WHEN operacao='D' THEN -vlrtot END), 0),
              COALESCE(SUM(CASE WHEN operacao='V' THEN vlrtot END), 0),
              COALESCE(SUM(CASE WHEN operacao='B' THEN -vlrtot END), 0),
              COUNT(DISTINCT CASE WHEN operacao='V' THEN codparc END),
              COUNT(DISTINCT CASE WHEN operacao='V' THEN nunota END),
              MAX(dtmov)
            FROM vw_venda WHERE {w}""", a).fetchone()
    m = conn.execute(
        f"""SELECT COALESCE(SUM(qtd_meta),0), COALESCE(SUM(vlr_previsto),0),
                   COALESCE(SUM(qtd_vendida),0), COALESCE(SUM(vlr_faturado),0),
                   COALESCE(SUM(qtd_fechada),0), COALESCE(SUM(vlr_fechado),0), COUNT(*)
            FROM vw_meta WHERE {w}""", a).fetchone()
    div = lambda x, y: x / y if y else None
    return {
        "faturado": v[0], "kg": v[1], "devolucao": v[2], "venda_bruta": v[3],
        "bonificacao": v[4], "clientes": v[5], "notas": v[6], "ultima_data": v[7],
        "perc_devolucao": div(v[2], v[3]), "ticket_medio": div(v[3], v[6]),
        "preco_medio": div(v[0], v[1]),
        "meta_kg": m[0], "meta_valor": m[1], "vendido_kg": m[2], "vendido_valor": m[3],
        "carteira_kg": m[4], "carteira_valor": m[5], "tem_meta": m[6] > 0,
        "perc_meta_kg": div(m[2], m[0]), "perc_meta_valor": div(m[3], m[1]),
        "perc_prev_kg": div(m[2] + m[4], m[0]),
    }


def vendas_diarias(conn, f: Filtro) -> pd.DataFrame:
    w, a = f.where()
    return _df(conn, f"""SELECT dtmov AS data,
                  SUM(CASE WHEN {REALIZADO} THEN vlrtot ELSE 0 END) AS faturado,
                  SUM(CASE WHEN {REALIZADO} THEN qtd_kg ELSE 0 END) AS kg
               FROM vw_venda WHERE {w} GROUP BY dtmov ORDER BY dtmov""", a)


def meta_por(conn, f: Filtro, dimensao: str) -> pd.DataFrame:
    """Meta x realizado agrupado por vendedor, supervisor, categoria, produto..."""
    assert dimensao in {"vendedor", "supervisor", "gerente", "categoria", "descrprod", "nomereg"}
    w, a = f.where()
    df = _df(conn, f"""SELECT {dimensao} AS grupo,
                  SUM(qtd_meta) AS meta_kg, SUM(qtd_vendida) AS vendido_kg,
                  SUM(qtd_fechada) AS carteira_kg, SUM(vlr_previsto) AS meta_valor,
                  SUM(vlr_faturado) AS vendido_valor, SUM(vlr_fechado) AS carteira_valor
               FROM vw_meta WHERE {w} GROUP BY {dimensao}""", a)
    df["perc_meta"] = df.vendido_kg / df.meta_kg.where(df.meta_kg > 0)
    df["perc_prev"] = (df.vendido_kg + df.carteira_kg) / df.meta_kg.where(df.meta_kg > 0)
    df["perc_meta_valor"] = df.vendido_valor / df.meta_valor.where(df.meta_valor > 0)
    return df.sort_values("meta_kg", ascending=False)


DIM_VENDAS = {"nomeparc", "descrprod", "uf", "cidade", "perfil", "rede", "mix_comercial", "mix_biblia", "linha",
              "vendedor", "supervisor", "gerente", "descroper", "grupoprod", "nomereg", "regiao_pais", "familia",
              "operacao", "nomeempresa", "dtmov", "origem"}


def vendas_por(conn, f: Filtro, dimensao: str, limite: int | None = None) -> pd.DataFrame:
    assert dimensao in DIM_VENDAS
    w, a = f.where()
    sql = f"""SELECT {dimensao} AS grupo,
                  SUM(CASE WHEN {REALIZADO} THEN vlrtot ELSE 0 END) AS faturado,
                  SUM(CASE WHEN {REALIZADO} THEN qtd_kg ELSE 0 END) AS kg,
                  SUM(CASE WHEN operacao='D' THEN -vlrtot ELSE 0 END) AS devolucao,
                  COUNT(DISTINCT CASE WHEN operacao='V' THEN codparc END) AS clientes,
                  COUNT(DISTINCT CASE WHEN operacao='V' THEN nunota END) AS notas
              FROM vw_venda WHERE {w} GROUP BY {dimensao} ORDER BY faturado DESC"""
    if limite:
        sql += f" LIMIT {int(limite)}"
    df = _df(conn, sql, a)
    df["preco_medio"] = df.faturado / df.kg.where(df.kg != 0)
    return df


def detalhe_vendas(conn, f: Filtro) -> pd.DataFrame:
    w, a = f.where()
    return _df(conn, f"SELECT * FROM vw_venda WHERE {w} ORDER BY dtmov, nunota", a)


def detalhe_metas(conn, f: Filtro) -> pd.DataFrame:
    w, a = f.where()
    return _df(conn, f"SELECT * FROM vw_meta WHERE {w} ORDER BY vendedor, descrprod", a)


def cargas(conn) -> pd.DataFrame:
    return _df(conn, "SELECT id, tipo, origem, arquivo, periodos, linhas, emitido_em, "
                     "usuario_relatorio, importado_em FROM carga ORDER BY id DESC")


def conciliacao(conn, periodo: str) -> pd.DataFrame:
    """Compara o 'Vendido' do resumo de metas importado com o realizado das notas.

    Diferenças costumam vir de notas emitidas entre a extração de um relatório
    e do outro, ou de notas lançadas em outra região/vendedor.
    """
    return _df(conn, """
        SELECT nomereg AS regiao, vendedor, descrprod AS produto,
               vendido_rel AS kg_resumo, qtd_vendida AS kg_notas, vendido_rel - qtd_vendida AS dif_kg,
               faturado_rel AS valor_resumo, vlr_faturado AS valor_notas, faturado_rel - vlr_faturado AS dif_valor
        FROM vw_meta
        WHERE periodo = ? AND vendido_rel IS NOT NULL
          AND (ABS(vendido_rel - qtd_vendida) > 0.01 OR ABS(faturado_rel - vlr_faturado) > 0.05)
        ORDER BY ABS(faturado_rel - vlr_faturado) DESC""", (periodo,))
