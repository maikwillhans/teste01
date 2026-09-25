"""Importação das planilhas exportadas para a base.

Fluxo: ler arquivo -> detectar tipo pelo título/cabeçalho -> validar colunas
-> normalizar tipos -> atualizar cadastros (vendedores, clientes, produtos,
regiões, TOPs, empresas) -> substituir os lançamentos importados do período
-> registrar a carga. Uma carga é atômica: ou entra inteira, ou nada muda.

Lançamentos feitos à mão (origem 'manual') não são apagados por uma
importação, a não ser que a planilha traga uma nota com o mesmo Nº Único.

A mesma função ``gravar`` recebe DataFrames já normalizados, então uma carga
vinda direto do Sankhya (``vendas_bi/sankhya/``) usa exatamente o mesmo caminho.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from .layouts import LAYOUTS, METAS, VENDAS

COLUNAS_FATO = {
    VENDAS: [
        "periodo", "dtmov", "codemp", "nunota", "numnota", "codtipoper", "descroper",
        "operacao", "codparc", "nomeparc", "perfil", "cidade", "uf", "regiao_pais",
        "codrede", "rede", "codreg", "nomereg", "codvend", "vendedor", "supervisor",
        "gerente", "codprod", "descrprod", "codgrupoprod", "grupoprod", "linha",
        "familia", "codmix_comercial", "mix_comercial", "codmix_biblia", "mix_biblia",
        "qtd_kg", "vlrtot", "vlrsubst", "vlrtot_st", "nucte", "ref_rvv",
    ],
    METAS: [
        "periodo", "codreg", "nomereg", "vendedor", "vendedor_ativo", "supervisor",
        "gerente", "categoria", "codprod", "descrprod", "qtd_meta", "pm_meta",
        "qtd_vendida", "vlr_faturado", "qtd_fechada", "vlr_fechado",
    ],
}


class ErroImportacao(ValueError):
    pass


@dataclass
class Relatorio:
    tipo: str
    dados: pd.DataFrame                 # já normalizado (colunas da base)
    emitido_em: datetime | None = None
    usuario: str | None = None
    avisos: list[str] = field(default_factory=list)
    controle: dict | None = None        # totais lidos direto das células

    @property
    def periodos(self) -> list[str]:
        return sorted(self.dados["periodo"].dropna().unique())


@dataclass
class ResultadoCarga:
    carga_id: int | None
    tipo: str
    periodos: list[str]
    linhas: int
    substituidas: int
    avisos: list[str]
    ignorada: bool = False


# --------------------------------------------------------------------- leitura

def _ler_bruto(origem, nome: str) -> pd.DataFrame:
    ext = Path(nome).suffix.lower()
    if isinstance(origem, (bytes, bytearray)):
        origem = io.BytesIO(origem)
    if ext == ".csv":
        return pd.read_csv(origem, header=None, dtype=object, sep=None, engine="python")
    engine = "xlrd" if ext == ".xls" else "openpyxl"
    return pd.read_excel(origem, header=None, dtype=object, engine=engine)


def _achar_cabecalho(bruto: pd.DataFrame) -> tuple[str, int]:
    """Procura, nas primeiras linhas, o cabeçalho de algum layout conhecido."""
    for i in range(min(15, len(bruto))):
        valores = {str(v).strip() for v in bruto.iloc[i].tolist() if pd.notna(v)}
        for tipo, layout in LAYOUTS.items():
            if set(layout["obrigatorias"]) <= valores:
                return tipo, i
    raise ErroImportacao(
        "Planilha não reconhecida. Esperado 'Demonstrativo Mensal das Vendas "
        "Efetuadas' ou 'Resumo Geral das Metas/Vendas' exportado do sistema."
    )


def _info_emissao(bruto: pd.DataFrame, linha_cab: int) -> tuple[datetime | None, str | None, int | None]:
    texto = " ".join(
        str(v) for v in bruto.iloc[:linha_cab].to_numpy().ravel() if pd.notna(v)
    )
    emitido = usuario = total = None
    if m := re.search(r"Emiss[aã]o:\s*(\d{2}/\d{2}/\d{4})(?:\s+(\d{2}:\d{2}:\d{2}))?", texto):
        emitido = datetime.strptime(" ".join(g for g in m.groups() if g), "%d/%m/%Y %H:%M:%S" if m.group(2) else "%d/%m/%Y")
    if m := re.search(r"Usu[aá]rio:\s*(.+?)\s*$", texto):
        usuario = m.group(1)
    if m := re.search(r"Total de registros:\s*(\d+)", texto):
        total = int(m.group(1))
    return emitido, usuario, total


def _para_data(serie: pd.Series) -> pd.Series:
    def conv(v):
        if pd.isna(v):
            return None
        if isinstance(v, (datetime, date, pd.Timestamp)):
            return pd.Timestamp(v).strftime("%Y-%m-%d")
        if isinstance(v, (int, float)):  # número de série do Excel
            return (pd.Timestamp("1899-12-30") + pd.Timedelta(days=float(v))).strftime("%Y-%m-%d")
        return datetime.strptime(str(v).strip()[:10], "%d/%m/%Y").strftime("%Y-%m-%d")
    return serie.map(conv)


def _converter(serie: pd.Series, tipo: str) -> pd.Series:
    if tipo == "str":
        return serie.map(lambda v: None if pd.isna(v) or str(v).strip() == "" else str(v).strip())
    if tipo == "date":
        return _para_data(serie)
    num = pd.to_numeric(serie, errors="coerce")
    if tipo == "int":
        return num.round().astype("Int64")
    return num.fillna(0.0).astype(float)


def _separar_regiao(serie: pd.Series) -> tuple[pd.Series, pd.Series]:
    partes = serie.fillna("").str.split(" - ", n=1, expand=True).reindex(columns=[0, 1])
    cod = pd.to_numeric(partes[0], errors="coerce").astype("Int64")
    nome = partes[1].where(cod.notna(), serie)
    return cod, nome


def ler_relatorio(origem, nome: str, periodo_meta: str | None = None, todas: bool = False) -> Relatorio:
    """Lê e normaliza um relatório. ``origem`` = caminho, bytes ou arquivo aberto.

    ``periodo_meta`` (AAAA-MM) define o mês das metas; se omitido usa o mês da
    data de emissão do relatório, já que o resumo de metas não traz o período.
    ``todas`` mantém também as colunas calculadas do relatório (``*_rel``).
    """
    bruto = _ler_bruto(origem, nome)
    tipo, linha_cab = _achar_cabecalho(bruto)
    layout = LAYOUTS[tipo]
    emitido, usuario, total = _info_emissao(bruto, linha_cab)

    cab = [str(v).strip() if pd.notna(v) else "" for v in bruto.iloc[linha_cab]]
    df = bruto.iloc[linha_cab + 1:].copy()
    df.columns = cab
    avisos: list[str] = []

    faltando = [c for c in layout["colunas"] if c not in df.columns and layout["colunas"][c][0]]
    if faltando:
        raise ErroImportacao(f"Colunas ausentes no relatório de {tipo}: {', '.join(faltando)}")
    extras = [c for c in df.columns if c and c not in layout["colunas"]]
    if extras:
        avisos.append(f"Colunas ignoradas (não mapeadas): {', '.join(extras)}")

    # linha de totais do rodapé e linhas vazias: sem chave obrigatória
    chave = [c for c in layout["obrigatorias"] if layout["colunas"][c][1] == "str"] or layout["obrigatorias"][:1]
    df = df[df[chave].notna().all(axis=1) & (df[chave].astype(str).apply(lambda s: s.str.strip()) != "").all(axis=1)]

    saida = pd.DataFrame(index=df.index)
    for origem_col, (destino, tipo_col, _) in layout["colunas"].items():
        if destino:
            saida[destino] = _converter(df[origem_col], tipo_col)
    saida["codreg"], saida["nomereg"] = _separar_regiao(saida.pop("regiao"))

    if tipo == VENDAS:
        saida["periodo"] = saida["dtmov"].str[:7]
    else:
        if periodo_meta is None:
            if emitido is None:
                raise ErroImportacao("Informe o mês de referência das metas (AAAA-MM).")
            periodo_meta = emitido.strftime("%Y-%m")
        if not re.fullmatch(r"\d{4}-\d{2}", periodo_meta):
            raise ErroImportacao(f"Período inválido: {periodo_meta!r} (use AAAA-MM)")
        saida["periodo"] = periodo_meta

    if total is not None and total != len(saida):
        avisos.append(f"Relatório informa {total} registros, foram lidos {len(saida)}.")
    if saida.empty:
        raise ErroImportacao("Nenhuma linha de dados encontrada no relatório.")

    colunas = COLUNAS_FATO[tipo] + ([c for c in saida.columns if c.endswith("_rel")] if todas else [])
    controle = _controle(bruto.iloc[linha_cab + 1:].set_axis(cab, axis=1), tipo, total)
    return Relatorio(tipo, saida[colunas].reset_index(drop=True), emitido, usuario, avisos, controle)


CONTROLE = {
    VENDAS: {"somas": ["Qtde Kg", "Valor Total Produto", "Valor Total Com ST", "Valor ST"],
             "distintos": ["Nº Único Nota", "Cód. Cliente", "Cód.Produto", "Cód. Vendedor"],
             "contagem": "Operação"},
    METAS: {"somas": ["Vendido", "Meta", "Fechado", "Valor Fechado", "Valor Faturado", "Valor Fat. Previsto"],
            "distintos": ["Vendedor", "Cód.", "Região"],
            "contagem": "Categoria"},
}


def _controle(df: pd.DataFrame, tipo: str, total: int | None) -> dict:
    """Totais das células originais, usados depois para conferir a base."""
    cfg = CONTROLE[tipo]
    chave = df[LAYOUTS[tipo]["obrigatorias"][0]]
    df = df[chave.notna() & (chave.astype(str).str.strip() != "")]
    num = lambda c: pd.to_numeric(df[c], errors="coerce").fillna(0)
    return {
        "linhas": int(len(df)), "total_informado": total,
        "somas": {c: round(float(num(c).sum()), 4) for c in cfg["somas"]},
        "distintos": {c: int(df[c].dropna().astype(str).str.strip().replace("", pd.NA).dropna().nunique()) for c in cfg["distintos"]},
        "contagem_campo": cfg["contagem"],
        "contagem": {str(k): int(v) for k, v in df[cfg["contagem"]].astype(str).str.strip().value_counts().items()},
    }


# --------------------------------------------------------------------- gravação

def _linhas(df: pd.DataFrame, colunas: list[str]):
    sub = df[colunas].astype(object)
    return [tuple(None if pd.isna(v) else v for v in r) for r in sub.itertuples(index=False, name=None)]


def _upsert(conn, tabela: str, chave: str, df: pd.DataFrame, colunas: list[str], atualizar: list[str] | None = None):
    """Insere ou atualiza cadastros. Campos vazios na planilha não apagam o que já existe."""
    atualizar = colunas if atualizar is None else atualizar
    todas = [chave, *colunas]
    sets = ", ".join(f"{c} = COALESCE(excluded.{c}, {c})" for c in atualizar)
    sql = (f"INSERT INTO {tabela} ({','.join(todas)}) VALUES ({','.join('?' * len(todas))}) "
           f"ON CONFLICT({chave}) DO " + (f"UPDATE SET {sets}" if sets else "NOTHING"))
    conn.executemany(sql, _linhas(df.drop_duplicates(chave), todas))


def _cadastros_regiao(conn, df):
    reg = df.dropna(subset=["codreg"])[["codreg", "nomereg"]]
    _upsert(conn, "regiao", "codreg", reg, ["nomereg"])


def _garantir_vendedor(conn, codvend: int, apelido: str) -> None:
    """Se o apelido já existe com outro código provisório, assume o código real."""
    atual = conn.execute("SELECT codvend, provisorio FROM vendedor WHERE apelido = ?", (apelido,)).fetchone()
    if atual and atual[0] != codvend:
        if atual[1]:
            conn.execute("UPDATE vendedor SET codvend = ?, provisorio = 0 WHERE apelido = ?", (codvend, apelido))
        else:
            conn.execute("UPDATE vendedor SET apelido = apelido || ' (' || codvend || ')' WHERE apelido = ?", (apelido,))


def _gravar_vendas(conn, df: pd.DataFrame, carga_id: int, origem: str) -> int:
    empresas = df[["codemp"]].dropna().drop_duplicates()
    empresas["nomeempresa"] = "Empresa " + empresas["codemp"].astype(str)
    _upsert(conn, "empresa", "codemp", empresas, ["nomeempresa"], atualizar=[])
    _cadastros_regiao(conn, df)
    vend = df.dropna(subset=["codvend"]).copy()
    reg_vend = vend.groupby("codvend")["codreg"].agg(lambda s: s.mode().iloc[0] if s.notna().any() else None)
    vend = vend.drop_duplicates("codvend")[["codvend", "vendedor", "supervisor", "gerente"]].rename(columns={"vendedor": "apelido"})
    vend["codreg"] = vend["codvend"].map(reg_vend)
    for codvend, apelido in vend[["codvend", "apelido"]].itertuples(index=False):
        _garantir_vendedor(conn, int(codvend), apelido)
    _upsert(conn, "vendedor", "codvend", vend, ["apelido", "supervisor", "gerente", "codreg"])
    conn.execute("UPDATE vendedor SET provisorio = 0 WHERE codvend IN (%s)" % ",".join(str(int(c)) for c in vend.codvend))
    _upsert(conn, "parceiro", "codparc", df, ["nomeparc", "perfil", "cidade", "uf", "regiao_pais", "codrede", "rede"])
    _upsert(conn, "produto", "codprod", df, ["descrprod", "codgrupoprod", "grupoprod", "linha", "familia",
                                               "codmix_comercial", "mix_comercial", "codmix_biblia", "mix_biblia"])
    _upsert(conn, "tipo_operacao", "codtipoper", df, ["descroper", "operacao"])

    periodos = sorted(df["periodo"].unique())
    nunotas = [int(n) for n in df["nunota"].unique()]
    removidas = conn.execute(
        f"SELECT COUNT(*) FROM item i JOIN nota n ON n.nunota = i.nunota WHERE "
        f"(substr(n.dtmov,1,7) IN ({','.join('?' * len(periodos))}) AND n.origem <> 'manual')",
        periodos).fetchone()[0]
    conn.execute(f"DELETE FROM nota WHERE substr(dtmov,1,7) IN ({','.join('?' * len(periodos))}) AND origem <> 'manual'", periodos)
    for i in range(0, len(nunotas), 500):
        lote = nunotas[i:i + 500]
        conn.execute(f"DELETE FROM nota WHERE nunota IN ({','.join('?' * len(lote))})", lote)

    cab = df.drop_duplicates("nunota")[["nunota", "numnota", "codemp", "dtmov", "codtipoper", "codparc", "codvend", "codreg", "ref_rvv"]]
    conn.executemany(
        "INSERT INTO nota (nunota, numnota, codemp, dtmov, codtipoper, codparc, codvend, codreg, ref_rvv, origem, carga_id) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [(*r, origem, carga_id) for r in _linhas(cab, list(cab.columns))])
    itens = df[["nunota", "codprod", "qtd_kg", "vlrtot", "vlrsubst", "vlrtot_st", "nucte"]].copy()
    itens.insert(1, "sequencia", itens.groupby("nunota").cumcount() + 1)
    conn.executemany(
        "INSERT INTO item (nunota, sequencia, codprod, qtd_kg, vlrtot, vlrsubst, vlrtot_st, nucte) VALUES (?,?,?,?,?,?,?,?)",
        _linhas(itens, list(itens.columns)))
    return removidas


def _gravar_metas(conn, df: pd.DataFrame, carga_id: int, origem: str) -> int:
    _cadastros_regiao(conn, df)
    prox = conn.execute("SELECT MAX(900000, COALESCE(MAX(codvend), 0) + 1) FROM vendedor").fetchone()[0]
    codigos = {}
    for apelido, sup, ger, codreg, ativo in df.drop_duplicates("vendedor")[
            ["vendedor", "supervisor", "gerente", "codreg", "vendedor_ativo"]].astype(object).itertuples(index=False):
        ativo = "N" if str(ativo).strip().lower().startswith("n") else "S"
        r = conn.execute("SELECT codvend FROM vendedor WHERE apelido = ?", (apelido,)).fetchone()
        if r:
            conn.execute("UPDATE vendedor SET supervisor = COALESCE(?, supervisor), gerente = COALESCE(?, gerente), ativo = ? "
                         "WHERE codvend = ?", (sup, ger, ativo, r[0]))
            codigos[apelido] = r[0]
        else:  # vendedor sem venda: recebe código provisório até vir o código real
            conn.execute("INSERT INTO vendedor (codvend, apelido, supervisor, gerente, codreg, ativo, provisorio) "
                         "VALUES (?,?,?,?,?,?,1)", (prox, apelido, sup, ger, None if pd.isna(codreg) else int(codreg), ativo))
            codigos[apelido] = prox
            prox += 1
    for codprod, descr, cat in df.drop_duplicates("codprod")[["codprod", "descrprod", "categoria"]].itertuples(index=False):
        conn.execute("INSERT INTO produto (codprod, descrprod, categoria) VALUES (?,?,?) "
                     "ON CONFLICT(codprod) DO UPDATE SET categoria = COALESCE(excluded.categoria, categoria)",
                     (int(codprod), descr, cat))

    periodos = sorted(df["periodo"].unique())
    marc = ",".join("?" * len(periodos))
    removidas = conn.execute(f"SELECT COUNT(*) FROM meta WHERE periodo IN ({marc}) AND origem <> 'manual'", periodos).fetchone()[0]
    conn.execute(f"DELETE FROM meta WHERE periodo IN ({marc}) AND origem <> 'manual'", periodos)
    m = df.copy()
    m["codvend"] = m["vendedor"].map(codigos)
    colunas = ["periodo", "codreg", "codvend", "codprod", "qtd_meta", "pm_meta", "qtd_fechada", "vlr_fechado",
               "qtd_vendida", "vlr_faturado"]
    conn.executemany(
        "INSERT INTO meta (periodo, codreg, codvend, codprod, qtd_meta, pm_meta, qtd_fechada, vlr_fechado, "
        "vendido_rel, faturado_rel, origem, carga_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(periodo, codreg, codvend, codprod) DO UPDATE SET qtd_meta = excluded.qtd_meta, "
        "pm_meta = excluded.pm_meta, qtd_fechada = excluded.qtd_fechada, vlr_fechado = excluded.vlr_fechado, "
        "vendido_rel = excluded.vendido_rel, faturado_rel = excluded.faturado_rel, origem = excluded.origem, "
        "carga_id = excluded.carga_id",
        [(*r, origem, carga_id) for r in _linhas(m, colunas)])
    return removidas


def gravar(conn: sqlite3.Connection, rel: Relatorio, arquivo: str | None = None,
           sha256: str | None = None, origem: str = "planilha") -> ResultadoCarga:
    """Atualiza cadastros e substitui os lançamentos importados dos períodos do relatório."""
    periodos = rel.periodos
    with conn:
        cur = conn.execute(
            "INSERT INTO carga (tipo, origem, arquivo, sha256, periodos, linhas, emitido_em, usuario_relatorio, controle) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (rel.tipo, origem, arquivo, sha256, ",".join(periodos), len(rel.dados),
             rel.emitido_em.isoformat(sep=" ") if rel.emitido_em else None, rel.usuario,
             json.dumps(rel.controle, ensure_ascii=False) if rel.controle else None),
        )
        carga_id = cur.lastrowid
        if rel.tipo == VENDAS:
            removidas = _gravar_vendas(conn, rel.dados, carga_id, origem)
        else:
            removidas = _gravar_metas(conn, rel.dados, carga_id, origem)
    return ResultadoCarga(carga_id, rel.tipo, periodos, len(rel.dados), removidas, rel.avisos)


def desfazer_carga(conn: sqlite3.Connection, carga_id: int) -> dict:
    """Remove os lançamentos que vieram de uma carga (os cadastros ficam)."""
    with conn:
        notas = conn.execute("DELETE FROM nota WHERE carga_id = ?", (carga_id,)).rowcount
        metas = conn.execute("DELETE FROM meta WHERE carga_id = ?", (carga_id,)).rowcount
        conn.execute("DELETE FROM carga WHERE id = ?", (carga_id,))
    return {"notas": notas, "metas": metas}


def importar(conn: sqlite3.Connection, origem, nome: str | None = None,
             periodo_meta: str | None = None, forcar: bool = False) -> ResultadoCarga:
    """Lê um arquivo e grava na base. Arquivo idêntico ao último importado é ignorado."""
    if isinstance(origem, (str, Path)):
        nome = nome or Path(origem).name
        conteudo = Path(origem).read_bytes()
    elif isinstance(origem, (bytes, bytearray)):
        conteudo = bytes(origem)
    else:
        conteudo = origem.read()
    if not nome:
        raise ErroImportacao("Informe o nome do arquivo.")
    sha = hashlib.sha256(conteudo).hexdigest()

    rel = ler_relatorio(conteudo, nome, periodo_meta)
    if not forcar:
        ja = conn.execute(
            "SELECT id FROM carga WHERE sha256 = ? AND tipo = ? AND periodos = ? ORDER BY id DESC LIMIT 1",
            (sha, rel.tipo, ",".join(rel.periodos)),
        ).fetchone()
        tabela = "nota" if rel.tipo == VENDAS else "meta"
        ultima = conn.execute(f"SELECT MAX(carga_id) FROM {tabela}").fetchone()[0]
        if ja and ultima == ja[0]:
            return ResultadoCarga(ja[0], rel.tipo, rel.periodos, len(rel.dados), 0,
                                  ["Arquivo idêntico já importado; nada foi alterado."], ignorada=True)
    return gravar(conn, rel, arquivo=nome, sha256=sha)
