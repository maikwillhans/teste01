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


def _conta(conn, tabela):
    return conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


def test_importacao_alimenta_cadastros_e_lancamentos(conn):
    importar(conn, _planilha(METAS, [_meta(), _meta(**{"Vendedor": "SEM VENDA", "Cód.": 240, "Produto": "LOMBO"})]), "m.xlsx")
    # vendedores do resumo ainda sem código real recebem código provisório
    assert conn.execute("SELECT COUNT(*) FROM vendedor WHERE provisorio = 1").fetchone()[0] == 2
    importar(conn, _planilha(VENDAS, [_venda(), _venda(**{"Cód.Produto": 240, "Descrição Produto": "LOMBO"})]), "v.xlsx")
    assert conn.execute("SELECT codvend, provisorio FROM vendedor WHERE apelido = 'ANDRIELLE'").fetchone() == (410, 0)
    assert conn.execute("SELECT provisorio FROM vendedor WHERE apelido = 'SEM VENDA'").fetchone() == (1,)
    # a meta acompanhou a troca do código provisório pelo real
    assert conn.execute("SELECT COUNT(*) FROM meta WHERE codvend = 410").fetchone()[0] == 1
    assert (_conta(conn, "nota"), _conta(conn, "item"), _conta(conn, "parceiro"), _conta(conn, "produto")) == (1, 2, 1, 2)
    assert conn.execute("SELECT categoria FROM produto WHERE codprod = 239").fetchone() == ("CONGELADOS AS",)
    assert conn.execute("SELECT nomereg FROM regiao WHERE codreg = 101003008").fetchone() == ("ZV106 - ANDRIELLE",)


def test_reimportar_substitui_mes_preserva_manual_e_ignora_duplicado(conn):
    from vendas_bi import servicos

    v1 = _planilha(VENDAS, [_venda(), _venda(**{"Nº Único Nota": 1001})])
    r = importar(conn, v1, "v.xlsx")
    assert (r.linhas, r.substituidas) == (2, 0)
    assert importar(conn, v1, "v.xlsx").ignorada

    manual = servicos.salvar_nota(conn, {"codemp": 1, "codtipoper": 500, "codparc": 10, "codvend": 410,
                                         "dtmov": "2026-09-20", "itens": [{"codprod": 239, "qtd_kg": 10, "vlrtot": 150}]})
    v2 = _planilha(VENDAS, [_venda(**{"Valor Total Produto": 999.0})])
    r = importar(conn, v2, "v.xlsx")
    assert (r.linhas, r.substituidas) == (1, 2)
    assert conn.execute("SELECT SUM(vlrtot) FROM item").fetchone()[0] == 999.0 + 150.0
    assert conn.execute("SELECT origem FROM nota WHERE nunota = ?", (manual["nunota"],)).fetchone() == ("manual",)

    # outro mês não apaga setembro
    importar(conn, _planilha(VENDAS, [_venda(**{"Data Mvto": "01/10/2026", "Nº Único Nota": 2000})]), "out.xlsx")
    assert q.periodos(conn) == ["2026-10", "2026-09"]


def test_desfazer_carga(conn):
    from vendas_bi.importer import desfazer_carga

    r = importar(conn, _planilha(VENDAS, [_venda()]), "v.xlsx")
    assert desfazer_carga(conn, r.carga_id) == {"notas": 1, "metas": 0}
    assert _conta(conn, "nota") == 0 and _conta(conn, "carga") == 0
    assert _conta(conn, "parceiro") == 1   # cadastros continuam


def test_indicadores_e_formulas_da_meta(conn):
    importar(conn, _planilha(METAS, [_meta()]), "m.xlsx")
    importar(conn, _planilha(VENDAS, [
        _venda(),
        _venda(**{"Operação": "D", "Qtde Kg": -10, "Valor Total Produto": -150.0, "TOP": 241, "Nº Único Nota": 1001}),
        _venda(**{"Operação": "B", "Qtde Kg": -5, "Valor Total Produto": -75.0, "TOP": 501, "Nº Único Nota": 1002}),
    ]), "v.xlsx")

    m = conn.execute("SELECT codvend, qtd_vendida, vlr_faturado, vlr_previsto, perc_meta, perc_prev, previa, vendido_rel "
                     "FROM vw_meta").fetchone()
    assert m == (410, 90.0, 1350.0, 3000.0, 0.45, 0.7, 60.0, 90.0)   # realizado das notas = vendido do resumo

    k = q.indicadores(conn, q.Filtro("2026-09"))
    assert k["faturado"] == 1350.0          # venda - devolução, sem bonificação
    assert k["kg"] == 90.0
    assert k["devolucao"] == 150.0 and k["bonificacao"] == 75.0
    assert k["perc_meta_kg"] == 0.45 and k["perc_meta_valor"] == 0.45
    assert q.conciliacao(conn, "2026-09").empty


def test_filtro_por_vendedor(conn):
    importar(conn, _planilha(VENDAS, [_venda(), _venda(**{"Vendedor": "OUTRO", "Cód. Vendedor": 1, "Nº Único Nota": 1001})]), "v.xlsx")
    k = q.indicadores(conn, q.Filtro("2026-09", vendedores=["OUTRO"]))
    assert k["faturado"] == 1500.0


def test_validacao_confere_importacao(conn):
    from vendas_bi.servicos import validar

    importar(conn, _planilha(METAS, [_meta()]), "m.xlsx")
    importar(conn, _planilha(VENDAS, [_venda()]), "v.xlsx")
    erros = [r for r in validar(conn, "2026-09") if r["estado"] == "erro"]
    assert erros == []


def test_mes_das_metas_pelas_vendas_e_troca_de_mes(conn):
    from vendas_bi.importer import mudar_periodo_carga

    # vendas de agosto e de setembro na base
    importar(conn, _planilha(VENDAS, [_venda(**{"Data Mvto": "10/08/2026", "Qtde Kg": 80, "Nº Único Nota": 1})]), "ago.xlsx")
    importar(conn, _planilha(VENDAS, [_venda(**{"Nº Único Nota": 2})]), "set.xlsx")
    # resumo de agosto emitido em setembro: o 'Vendido' (80 kg) bate com agosto
    r = importar(conn, _planilha(METAS, [_meta(**{"Vendido": 80})], emissao="02/09/2026 08:00:00"), "m_ago.xlsx")
    assert r.periodos == ["2026-08"] and "identificado pelas vendas" in r.avisos[0]
    r = importar(conn, _planilha(METAS, [_meta(**{"Vendido": 100})], emissao="25/09/2026 08:00:00"), "m_set.xlsx")
    assert r.periodos == ["2026-09"]
    assert q.periodos(conn) == ["2026-09", "2026-08"]
    assert conn.execute("SELECT COUNT(*) FROM meta").fetchone()[0] == 2

    # mês informado errado pode ser corrigido depois
    r = importar(conn, _planilha(METAS, [_meta(**{"Vendido": 80, "Meta": 999})]), "m.xlsx", periodo_meta="2026-10")
    assert mudar_periodo_carga(conn, r.carga_id, "2026-08") == 1
    assert conn.execute("SELECT qtd_meta FROM meta WHERE periodo = '2026-08'").fetchone() == (999.0,)


def test_linhas_repetidas_no_resumo_sao_somadas(conn):
    r = importar(conn, _planilha(METAS, [_meta(), _meta(**{"Meta": 100, "P.M. Meta": 30})]), "m.xlsx")
    assert any("somadas" in a for a in r.avisos)
    assert conn.execute("SELECT qtd_meta, qtd_meta * pm_meta FROM meta").fetchone() == (300.0, 6000.0)
