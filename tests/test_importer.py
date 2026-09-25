"""Testes com planilhas sintéticas no mesmo layout dos relatórios do sistema."""

import io

import pandas as pd
import pytest

from vendas_bi import consultas as q
from vendas_bi.db import conectar
from vendas_bi.importer import ErroImportacao, importar, ler_relatorio
from vendas_bi.layouts import LAYOUTS, METAS, VENDAS


def _planilha(tipo, linhas, emissao="25/09/2026 13:39:25"):
    cab = list(LAYOUTS[tipo]["colunas"])
    topo = [
        [LAYOUTS[tipo]["titulo"]] + [None] * (len(cab) - 1),
        [f"Emissão:{emissao}", f"Total de registros:{len(linhas)}", "Usuário: 172 - TESTE"]
        + [None] * (len(cab) - 3),
        cab,
    ]
    corpo = [[l.get(c) for c in cab] for l in linhas]
    rodape = [[None] * len(cab)]
    buf = io.BytesIO()
    pd.DataFrame(topo + corpo + rodape).to_excel(buf, header=False, index=False)
    return buf.getvalue()


def _venda(**kw):
    base = {
        "Ano": "2026", "Mês": "09", "Dia": "05", "Perfil Principal": "VAREJO",
        "Região": "101003008 - ZV106 - ANDRIELLE", "Nota Fiscal": 1, "Gerente": "MARLUCE",
        "Empresa": 1, "Supervisor": "MAYCON SORIO", "Vendedor": "ANDRIELLE", "Cód. Cliente": 10,
        "Cliente": "CLIENTE A", "Cidade": "CUIABA", "Uf": "MT", "Cód.Produto": 239,
        "Descrição Produto": "COSTELA", "Cód.Conta": "10102000", "Conta Estoque": "CONGELADOS",
        "Qtde Kg": 100, "Valor Total Produto": 1500.0, "Data Mvto": "05/09/2026",
        "Preço Médio": 15, "Valor Total Com ST": 1500.0, "Valor ST": 0, "Linha": "CONGELADOS",
        "TOP": 500, "Nome da TOP": "VENDA", "Nome Família": "SUINOS", "Operação": "V",
        "Cód Mix Comercial": 25, "Mix Comercial": "CONGELADOS - AS", "Cód Mix Bíblia": 40,
        "Mix Bíblia": "IN NATURA", "Cód. Rede": 1, "Cód. Vendedor": 410, "Nº CTE": None,
        "Nº Único Nota": 1000, "Rede": "SEM REDE", "Região País": "CENTRO-OESTE", "Ref. RVV": "09/2026",
    }
    base.update(kw)
    return base


def _meta(**kw):
    base = {
        "Vendedor Ativo?": "Sim", "Gerente": "MARLUCE", "Supervisor": "MAYCON SORIO",
        "Região": "101003008 - ZV106 - ANDRIELLE", "Vendedor": "ANDRIELLE",
        "Categoria": "CONGELADOS AS", "Cód.": 239, "Produto": "COSTELA", "Vendido": 90,
        "Meta": 200, "Fechado": 50, "Valor Fechado": 750, "P.M. Meta": 15, "% Meta": 45,
        "% Prev.": 70, "Diferença": 110, "P.M. Real.": 15, "Prévia": 60, "Valor Faturado": 1350,
        "Valor Fat. Previsto": 3000,
    }
    base.update(kw)
    return base


@pytest.fixture
def conn():
    return conectar(":memory:")


def test_detecta_e_normaliza_vendas():
    rel = ler_relatorio(_planilha(VENDAS, [_venda()]), "demo.xlsx")
    assert rel.tipo == VENDAS
    assert rel.periodos == ["2026-09"]
    linha = rel.dados.iloc[0]
    assert linha.codreg == 101003008 and linha.nomereg == "ZV106 - ANDRIELLE"
    assert linha.dtmov == "2026-09-05"
    assert linha.codgrupoprod == 10102000
    assert rel.usuario == "172 - TESTE"
    assert rel.avisos == []  # linha de rodapé descartada, total confere


def test_meta_usa_mes_da_emissao_ou_informado():
    arq = _planilha(METAS, [_meta()], emissao="02/10/2026 08:00:00")
    assert ler_relatorio(arq, "m.xlsx").periodos == ["2026-10"]
    assert ler_relatorio(arq, "m.xlsx", periodo_meta="2026-09").periodos == ["2026-09"]
    with pytest.raises(ErroImportacao):
        ler_relatorio(arq, "m.xlsx", periodo_meta="09/2026")


def test_planilha_desconhecida():
    buf = io.BytesIO()
    pd.DataFrame([["qualquer", "coisa"], [1, 2]]).to_excel(buf, header=False, index=False)
    with pytest.raises(ErroImportacao, match="não reconhecida"):
        ler_relatorio(buf.getvalue(), "x.xlsx")


def test_coluna_ausente():
    arq = _planilha(VENDAS, [_venda()])
    df = pd.read_excel(io.BytesIO(arq), header=None).drop(columns=[11])  # remove "Cliente"
    buf = io.BytesIO()
    df.to_excel(buf, header=False, index=False)
    with pytest.raises(ErroImportacao, match="Cliente"):
        ler_relatorio(buf.getvalue(), "x.xlsx")


def test_reimportar_substitui_periodo_e_ignora_duplicado(conn):
    v1 = _planilha(VENDAS, [_venda(), _venda(**{"Nº Único Nota": 1001})])
    r = importar(conn, v1, "v.xlsx")
    assert (r.linhas, r.substituidas) == (2, 0)
    assert importar(conn, v1, "v.xlsx").ignorada

    v2 = _planilha(VENDAS, [_venda(**{"Valor Total Produto": 999.0})])
    r = importar(conn, v2, "v.xlsx")
    assert (r.linhas, r.substituidas) == (1, 2)
    assert conn.execute("SELECT SUM(vlrtot) FROM fato_venda").fetchone()[0] == 999.0

    # outro mês não apaga setembro
    importar(conn, _planilha(VENDAS, [_venda(**{"Data Mvto": "01/10/2026"})]), "out.xlsx")
    assert q.periodos(conn) == ["2026-10", "2026-09"]


def test_indicadores_e_formulas_da_meta(conn):
    importar(conn, _planilha(VENDAS, [
        _venda(),
        _venda(**{"Operação": "D", "Qtde Kg": -10, "Valor Total Produto": -150.0, "TOP": 241}),
        _venda(**{"Operação": "B", "Qtde Kg": -5, "Valor Total Produto": -75.0, "TOP": 501}),
    ]), "v.xlsx")
    importar(conn, _planilha(METAS, [_meta()]), "m.xlsx")

    m = conn.execute("SELECT codvend, vlr_previsto, perc_meta, perc_prev, previa FROM vw_meta").fetchone()
    assert m == (410, 3000.0, 0.45, 0.7, 60.0)

    k = q.indicadores(conn, q.Filtro("2026-09"))
    assert k["faturado"] == 1350.0          # venda - devolução, sem bonificação
    assert k["kg"] == 90.0
    assert k["devolucao"] == 150.0 and k["bonificacao"] == 75.0
    assert k["perc_meta_kg"] == 0.45 and k["perc_meta_valor"] == 0.45
    assert q.conciliacao(conn, "2026-09").empty  # resumo bate com o demonstrativo


def test_filtro_por_vendedor(conn):
    importar(conn, _planilha(VENDAS, [_venda(), _venda(**{"Vendedor": "OUTRO", "Cód. Vendedor": 1})]), "v.xlsx")
    k = q.indicadores(conn, q.Filtro("2026-09", vendedores=["OUTRO"]))
    assert k["faturado"] == 1500.0
