"""Carga direta do Sankhya (fase 2) — substitui o upload de planilhas.

Executa as SQLs de ``vendas.sql``/``metas.sql`` pela API do Sankhya
(serviço ``DbExplorerSP.executeQuery``) e grava na base pelo mesmo caminho
da importação de planilhas (``importer.gravar``), com ``origem='sankhya'``.

NÃO TESTADO contra um ambiente Sankhya real: valide URL, forma de login e
permissões do usuário de integração com o TI. Credenciais por variável de
ambiente (nunca no código):

    SANKHYA_URL       ex.: https://api.sankhya.com.br
    SANKHYA_TOKEN     token do gateway
    SANKHYA_APPKEY    appkey da integração
    SANKHYA_USUARIO / SANKHYA_SENHA

Uso:  python -m vendas_bi.sankhya.conector 2026-09
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

from ..importer import COLUNAS_FATO, Relatorio, gravar
from ..layouts import METAS, VENDAS

AQUI = Path(__file__).parent


class ClienteSankhya:
    def __init__(self, url=None, token=None, appkey=None, usuario=None, senha=None):
        import requests

        self._http = requests.Session()
        self.url = (url or os.environ["SANKHYA_URL"]).rstrip("/")
        cab = {
            "token": token or os.environ["SANKHYA_TOKEN"],
            "appkey": appkey or os.environ["SANKHYA_APPKEY"],
            "username": usuario or os.environ["SANKHYA_USUARIO"],
            "password": senha or os.environ["SANKHYA_SENHA"],
        }
        r = self._http.post(f"{self.url}/login", headers=cab, timeout=60)
        r.raise_for_status()
        self._http.headers["Authorization"] = f"Bearer {r.json()['bearerToken']}"

    def consulta(self, sql: str) -> pd.DataFrame:
        corpo = {"serviceName": "DbExplorerSP.executeQuery", "requestBody": {"sql": sql}}
        r = self._http.post(
            f"{self.url}/gateway/v1/mge/service.sbr",
            params={"serviceName": "DbExplorerSP.executeQuery", "outputType": "json"},
            json=corpo, timeout=600,
        )
        r.raise_for_status()
        dados = r.json()
        if str(dados.get("status")) != "1":
            raise RuntimeError(f"Sankhya recusou a consulta: {dados.get('statusMessage')}")
        resp = dados["responseBody"]
        colunas = [c["name"].lower() for c in resp["fieldsMetadata"]]
        return pd.DataFrame(resp["rows"], columns=colunas)


def _sql(arquivo: str, periodo: str) -> str:
    inicio = pd.Timestamp(f"{periodo}-01")
    fim = inicio + pd.offsets.MonthEnd(0)
    sql = (AQUI / arquivo).read_text(encoding="utf-8")
    sql = "\n".join(l for l in sql.splitlines() if not l.lstrip().startswith("--"))
    return (sql.replace(":DTINI", f"TO_DATE('{inicio:%d/%m/%Y}','DD/MM/YYYY')")
               .replace(":DTFIM", f"TO_DATE('{fim:%d/%m/%Y}','DD/MM/YYYY')"))


def carregar_periodo(conn, periodo: str, cliente: ClienteSankhya | None = None) -> list:
    """Busca vendas e metas do mês no Sankhya e substitui o período na base."""
    cliente = cliente or ClienteSankhya()
    resultados = []
    for tipo, arquivo in ((VENDAS, "vendas.sql"), (METAS, "metas.sql")):
        df = cliente.consulta(_sql(arquivo, periodo))
        df["periodo"] = df["dtmov"].str[:7] if tipo == VENDAS else periodo
        faltando = set(COLUNAS_FATO[tipo]) - set(df.columns)
        if faltando:
            raise RuntimeError(f"SQL de {tipo} não devolveu: {', '.join(sorted(faltando))}")
        rel = Relatorio(tipo, df[COLUNAS_FATO[tipo]])
        resultados.append(gravar(conn, rel, arquivo=f"sankhya:{arquivo}", origem="sankhya"))
    return resultados


if __name__ == "__main__":
    from ..db import conectar

    for r in carregar_periodo(conectar(), sys.argv[1]):
        print(r)
