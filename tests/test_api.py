"""Testes da API: lançamentos manuais, cadastros e importação."""

import pytest
from fastapi.testclient import TestClient

from vendas_bi.api import criar_app
from vendas_bi.layouts import METAS, VENDAS

from .test_importer import _meta, _planilha, _venda


@pytest.fixture
def api(tmp_path):
    cliente = TestClient(criar_app(tmp_path / "t.db"))
    r = cliente.post("/api/importar", files={"arquivo": ("v.xlsx", _planilha(VENDAS, [_venda()]))})
    assert r.status_code == 200, r.text
    r = cliente.post("/api/importar", files={"arquivo": ("m.xlsx", _planilha(METAS, [_meta()]))})
    assert r.status_code == 200, r.text
    return cliente


def test_inicio_e_painel(api):
    ini = api.get("/api/inicio").json()
    assert ini["periodos"] == ["2026-09"] and ini["contagens"]["notas"] == 1
    assert set(ini["cadastros"]) == {"vendedores", "clientes", "produtos", "regioes", "tops", "empresas"}
    p = api.get("/api/painel", params={"periodo": "2026-09"}).json()
    assert p["indicadores"]["faturado"] == 1500.0 and p["clientes"][0]["grupo"] == "CLIENTE A"


def test_cadastro_crud_e_regras(api):
    r = api.post("/api/cadastros/clientes", json={"codparc": 77, "nomeparc": "NOVO CLIENTE", "uf": "MT"})
    assert r.status_code == 200 and r.json()["nomeparc"] == "NOVO CLIENTE"
    assert api.post("/api/cadastros/clientes", json={"codparc": 77, "nomeparc": "X"}).status_code == 400   # duplicado
    assert "obrigatório" in api.post("/api/cadastros/clientes", json={"codparc": 78}).json()["erro"]
    assert api.put("/api/cadastros/clientes/77", json={"cidade": "SINOP"}).json()["cidade"] == "SINOP"
    assert api.get("/api/cadastros/clientes", params={"busca": "novo"}).json()["total"] == 1
    # cliente com nota não pode ser excluído; o novo pode
    assert "usado em 1 notas" in api.delete("/api/cadastros/clientes/10").json()["erro"]
    assert api.delete("/api/cadastros/clientes/77").status_code == 200
    # FK inexistente
    r = api.post("/api/cadastros/vendedores", json={"codvend": 5, "apelido": "NOVO", "codreg": 123})
    assert r.status_code == 400 and "não existe" in r.json()["erro"]


def test_trocar_codigo_do_vendedor_atualiza_lancamentos(api):
    assert api.put("/api/cadastros/vendedores/410", json={"codvend": 4100}).status_code == 200
    assert api.get("/api/notas", params={"periodo": "2026-09"}).json()["linhas"][0]["codvend"] == 4100
    assert api.get("/api/metas", params={"periodo": "2026-09"}).json()[0]["codvend"] == 4100


def test_nota_manual_com_sinal_pela_top(api):
    nota = {"codemp": 1, "codtipoper": 241, "codparc": 10, "codvend": 410, "dtmov": "2026-09-10",
            "itens": [{"codprod": 239, "qtd_kg": "10", "vlrtot": "150,50", "vlrsubst": 1}]}
    assert api.post("/api/notas", json=nota).status_code == 400          # TOP 241 ainda não cadastrada
    api.post("/api/cadastros/tops", json={"codtipoper": 241, "descroper": "DEVOLUCAO", "operacao": "D"})
    r = api.post("/api/notas", json=nota).json()
    assert r["nunota"] >= 900_000_000 and r["origem"] == "manual" and r["codreg"] == 101003008
    assert (r["itens"][0]["qtd_kg"], r["itens"][0]["vlrtot"], r["itens"][0]["vlrtot_st"]) == (-10.0, -150.5, -151.5)
    k = api.get("/api/painel", params={"periodo": "2026-09"}).json()["indicadores"]
    assert k["faturado"] == 1500.0 - 150.5 and k["devolucao"] == 150.5
    # alterar e excluir
    nota["itens"].append({"codprod": 239, "qtd_kg": 1, "vlrtot": 10})
    assert len(api.put(f"/api/notas/{r['nunota']}", json=nota).json()["itens"]) == 2
    assert api.delete(f"/api/notas/{r['nunota']}").status_code == 200
    assert "pelo menos um item" in api.post("/api/notas", json={**nota, "itens": []}).json()["erro"]


def test_metas_manual_duplicidade_e_copia(api):
    base = {"periodo": "2026-09", "codvend": 410, "codprod": 239, "qtd_meta": 100, "pm_meta": 15}
    assert "Já existe" in api.post("/api/metas", json=base).json()["erro"]
    api.post("/api/cadastros/produtos", json={"codprod": 500, "descrprod": "NOVO PRODUTO"})
    m = api.post("/api/metas", json={**base, "codprod": 500}).json()
    assert m["vlr_previsto"] == 1500.0 and m["origem"] == "manual"
    assert api.put(f"/api/metas/{m['id']}", json={**base, "codprod": 500, "qtd_meta": 200}).json()["vlr_previsto"] == 3000.0
    assert api.post("/api/metas/copiar", json={"de": "2026-09", "para": "2026-10"}).json()["copiadas"] == 2
    assert len(api.get("/api/metas", params={"periodo": "2026-10"}).json()) == 2


def test_validacao_exportacao_e_desfazer(api):
    v = api.get("/api/validacao", params={"periodo": "2026-09"}).json()
    assert not [r for r in v if r["estado"] == "erro"]
    csv = api.get("/api/exportar/vendas.csv", params={"periodo": "2026-09"})
    assert csv.status_code == 200 and "nunota" in csv.text.splitlines()[0]
    cargas = api.get("/api/cargas").json()
    assert len(cargas) == 2
    assert api.delete(f"/api/cargas/{cargas[-1]['id']}").json() == {"notas": 1, "metas": 0}


def test_planilha_invalida(api):
    r = api.post("/api/importar", files={"arquivo": ("x.csv", b"a;b\n1;2\n")})
    assert r.status_code == 400 and "não reconhecida" in r.json()["erro"]
