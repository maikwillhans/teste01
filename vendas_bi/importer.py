"""Importação das planilhas exportadas para a base.

Fluxo: ler arquivo -> detectar tipo pelo título/cabeçalho -> validar colunas
-> normalizar tipos -> substituir os períodos presentes no arquivo -> registrar
a carga. Uma carga é atômica: ou entra inteira, ou nada muda.

A mesma função ``gravar`` recebe DataFrames já normalizados, então uma carga
vinda direto do Sankhya (``vendas_bi/sankhya/``) usa exatamente o mesmo caminho.
"""

from __future__ import annotations

import hashlib
import io
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


def ler_relatorio(origem, nome: str, periodo_meta: str | None = None) -> Relatorio:
    """Lê e normaliza um relatório. ``origem`` = caminho, bytes ou arquivo aberto.

    ``periodo_meta`` (AAAA-MM) define o mês das metas; se omitido usa o mês da
    data de emissão do relatório, já que o resumo de metas não traz o período.
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

    return Relatorio(tipo, saida[COLUNAS_FATO[tipo]].reset_index(drop=True), emitido, usuario, avisos)


# --------------------------------------------------------------------- gravação

def gravar(conn: sqlite3.Connection, rel: Relatorio, arquivo: str | None = None,
           sha256: str | None = None, origem: str = "planilha") -> ResultadoCarga:
    """Substitui na base os períodos do relatório pelos dados dele (atômico)."""
    tabela = LAYOUTS[rel.tipo]["tabela"]
    periodos = rel.periodos
    marcadores = ",".join("?" * len(periodos))
    dados = rel.dados.astype(object).where(rel.dados.notna(), None)
    with conn:
        cur = conn.execute(
            "INSERT INTO carga (tipo, origem, arquivo, sha256, periodos, linhas, emitido_em, usuario_relatorio) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (rel.tipo, origem, arquivo, sha256, ",".join(periodos), len(dados),
             rel.emitido_em.isoformat(sep=" ") if rel.emitido_em else None, rel.usuario),
        )
        carga_id = cur.lastrowid
        removidas = conn.execute(
            f"DELETE FROM {tabela} WHERE periodo IN ({marcadores})", periodos
        ).rowcount
        colunas = ["carga_id", *dados.columns]
        conn.executemany(
            f"INSERT INTO {tabela} ({','.join(colunas)}) VALUES ({','.join('?' * len(colunas))})",
            ([carga_id, *linha] for linha in dados.itertuples(index=False, name=None)),
        )
        _resolver_codvend(conn)
    return ResultadoCarga(carga_id, rel.tipo, periodos, len(dados), removidas, rel.avisos)


def _resolver_codvend(conn: sqlite3.Connection) -> None:
    """O resumo de metas não traz o código do vendedor; busca pelo apelido."""
    conn.execute(
        """UPDATE fato_meta SET codvend = (
               SELECT v.codvend FROM fato_venda v
               WHERE v.vendedor = fato_meta.vendedor AND v.codvend IS NOT NULL
               GROUP BY v.codvend ORDER BY COUNT(*) DESC LIMIT 1)
           WHERE codvend IS NULL"""
    )


def importar(conn: sqlite3.Connection, origem, nome: str | None = None,
             periodo_meta: str | None = None, forcar: bool = False) -> ResultadoCarga:
    """Lê um arquivo e grava na base. Arquivo idêntico já importado é ignorado."""
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
        ultima = conn.execute(
            f"SELECT MAX(carga_id) FROM {LAYOUTS[rel.tipo]['tabela']} WHERE periodo IN ({','.join('?' * len(rel.periodos))})",
            rel.periodos,
        ).fetchone()[0]
        if ja and ultima == ja[0]:
            return ResultadoCarga(ja[0], rel.tipo, rel.periodos, len(rel.dados), 0,
                                  ["Arquivo idêntico já importado; nada foi alterado."], ignorada=True)
    return gravar(conn, rel, arquivo=nome, sha256=sha)
