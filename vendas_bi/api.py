"""API do sistema (FastAPI). A interface web fica em /web e consome estas rotas."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import consultas as q
from . import servicos as s
from .db import BANCO_PADRAO, conectar
from .importer import ErroImportacao, desfazer_carga, importar

WEB = Path(__file__).resolve().parent.parent / "web"


def criar_app(caminho_banco: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="Vendas x Metas", version="1.0")
    conn = conectar(caminho_banco)
    app.state.conn = conn

    @app.exception_handler(s.ErroValidacao)
    async def _erro_validacao(_: Request, e: s.ErroValidacao):
        return JSONResponse({"erro": str(e)}, status_code=400)

    @app.exception_handler(ErroImportacao)
    async def _erro_importacao(_: Request, e: ErroImportacao):
        return JSONResponse({"erro": str(e)}, status_code=400)

    def registros(df: pd.DataFrame) -> list[dict]:
        return df.astype(object).where(df.notna(), None).to_dict(orient="records")

    def filtro(periodo, gerente, supervisor, vendedor) -> q.Filtro:
        return q.Filtro(periodo, [gerente] if gerente else None, [supervisor] if supervisor else None,
                        [vendedor] if vendedor else None)

    # ------------------------------------------------------------ geral
    @app.get("/api/inicio")
    def inicio():
        ps = q.periodos(conn)
        n = lambda t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        return {
            "periodos": ps, "cadastros": s.spec_publica(),
            "contagens": {"notas": n("nota"), "itens": n("item"), "metas": n("meta"), "cargas": n("carga"),
                          "vendedores": n("vendedor"), "clientes": n("parceiro"), "produtos": n("produto"),
                          "regioes": n("regiao"), "tops": n("tipo_operacao"), "empresas": n("empresa")},
            "banco": str(BANCO_PADRAO if caminho_banco is None else caminho_banco),
        }

    @app.get("/api/opcoes")
    def opcoes(periodo: str):
        return q.opcoes(conn, periodo)

    # ------------------------------------------------------------ painel
    @app.get("/api/painel")
    def painel(periodo: str, gerente: str = "", supervisor: str = "", vendedor: str = ""):
        f = filtro(periodo, gerente, supervisor, vendedor)
        return {
            "indicadores": q.indicadores(conn, f),
            "diarias": registros(q.vendas_diarias(conn, f)),
            "por_supervisor": registros(q.meta_por(conn, f, "supervisor")),
            "por_categoria": registros(q.meta_por(conn, f, "categoria")),
            "clientes": registros(q.vendas_por(conn, f, "nomeparc", 10)),
            "produtos": registros(q.vendas_por(conn, f, "descrprod", 10)),
            "perfis": registros(q.vendas_por(conn, f, "perfil", 10)),
            "ufs": registros(q.vendas_por(conn, f, "uf", 10)),
        }

    @app.get("/api/metas/resumo")
    def metas_resumo(periodo: str, dimensao: str = "vendedor", gerente: str = "", supervisor: str = "", vendedor: str = ""):
        if dimensao not in {"vendedor", "supervisor", "gerente", "categoria", "descrprod", "nomereg"}:
            raise s.ErroValidacao("Agrupamento inválido.")
        return registros(q.meta_por(conn, filtro(periodo, gerente, supervisor, vendedor), dimensao))

    @app.get("/api/vendas/resumo")
    def vendas_resumo(periodo: str, dimensao: str = "nomeparc", gerente: str = "", supervisor: str = "", vendedor: str = ""):
        if dimensao not in q.DIM_VENDAS:
            raise s.ErroValidacao("Agrupamento inválido.")
        return registros(q.vendas_por(conn, filtro(periodo, gerente, supervisor, vendedor), dimensao))

    # ------------------------------------------------------------ cadastros
    @app.get("/api/cadastros/{nome}")
    def cad_listar(nome: str, busca: str = "", pagina: int = 0, por_pagina: int = Query(50, le=500)):
        return s.listar_cadastro(conn, nome, busca, pagina, por_pagina)

    @app.get("/api/cadastros/{nome}/opcoes")
    def cad_opcoes(nome: str):
        return s.opcoes_cadastro(conn, nome)

    @app.post("/api/cadastros/{nome}")
    async def cad_criar(nome: str, request: Request):
        return s.salvar_cadastro(conn, nome, await request.json())

    @app.put("/api/cadastros/{nome}/{chave}")
    async def cad_alterar(nome: str, chave: int, request: Request):
        return s.salvar_cadastro(conn, nome, await request.json(), chave_atual=chave)

    @app.delete("/api/cadastros/{nome}/{chave}")
    def cad_excluir(nome: str, chave: int):
        s.excluir_cadastro(conn, nome, chave)
        return {"ok": True}

    # ------------------------------------------------------------ notas
    @app.get("/api/notas")
    def notas_listar(periodo: str = "", busca: str = "", origem: str = "", pagina: int = 0, por_pagina: int = Query(50, le=500)):
        return s.listar_notas(conn, periodo or None, busca, origem, pagina, por_pagina)

    @app.get("/api/notas/{nunota}")
    def notas_obter(nunota: int):
        return s.obter_nota(conn, nunota)

    @app.post("/api/notas")
    async def notas_criar(request: Request):
        return s.salvar_nota(conn, await request.json())

    @app.put("/api/notas/{nunota}")
    async def notas_alterar(nunota: int, request: Request):
        return s.salvar_nota(conn, await request.json(), nunota)

    @app.delete("/api/notas/{nunota}")
    def notas_excluir(nunota: int):
        s.excluir_nota(conn, nunota)
        return {"ok": True}

    # ------------------------------------------------------------ metas
    @app.get("/api/metas")
    def metas_listar(periodo: str, busca: str = "", gerente: str = "", supervisor: str = "", vendedor: str = ""):
        return s.listar_metas(conn, periodo, busca, vendedor, supervisor, gerente)

    @app.post("/api/metas")
    async def metas_criar(request: Request):
        return s.salvar_meta(conn, await request.json())

    @app.put("/api/metas/{meta_id}")
    async def metas_alterar(meta_id: int, request: Request):
        return s.salvar_meta(conn, await request.json(), meta_id)

    @app.delete("/api/metas/{meta_id}")
    def metas_excluir(meta_id: int):
        s.excluir_meta(conn, meta_id)
        return {"ok": True}

    @app.post("/api/metas/copiar")
    async def metas_copiar(request: Request):
        d = await request.json()
        return {"copiadas": s.copiar_metas(conn, d.get("de"), d.get("para"))}

    # ------------------------------------------------------------ importação e cargas
    @app.post("/api/importar")
    async def importar_planilha(arquivo: UploadFile = File(...), periodo_meta: str = Form(""), forcar: bool = Form(False)):
        r = importar(conn, await arquivo.read(), arquivo.filename, periodo_meta.strip() or None, forcar)
        return {"carga_id": r.carga_id, "tipo": r.tipo, "periodos": r.periodos, "linhas": r.linhas,
                "substituidas": r.substituidas, "avisos": r.avisos, "ignorada": r.ignorada}

    @app.get("/api/cargas")
    def cargas():
        return registros(q.cargas(conn))

    @app.delete("/api/cargas/{carga_id}")
    def cargas_desfazer(carga_id: int):
        return desfazer_carga(conn, carga_id)

    @app.get("/api/validacao")
    def validacao(periodo: str):
        return s.validar(conn, periodo)

    @app.get("/api/conciliacao")
    def conciliacao(periodo: str):
        return registros(q.conciliacao(conn, periodo))

    # ------------------------------------------------------------ exportação
    @app.get("/api/exportar/{tipo}.csv")
    def exportar(tipo: str, periodo: str, gerente: str = "", supervisor: str = "", vendedor: str = ""):
        f = filtro(periodo, gerente, supervisor, vendedor)
        if tipo == "vendas":
            df = q.detalhe_vendas(conn, f)
        elif tipo == "metas":
            df = q.detalhe_metas(conn, f)
        else:
            raise HTTPException(404)
        conteudo = df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
        return Response(conteudo, media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="{tipo}_{periodo}.csv"'})

    @app.get("/api/exportar/base.db")
    def exportar_base():
        conn.execute("PRAGMA wal_checkpoint(FULL)")
        caminho = Path(caminho_banco or BANCO_PADRAO)
        if not caminho.exists():
            raise HTTPException(404)
        return FileResponse(caminho, filename="sistema_vendas_metas.db")

    # ------------------------------------------------------------ interface
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
    return app
