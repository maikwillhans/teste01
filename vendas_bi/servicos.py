"""Regras de negócio para lançamento manual: cadastros, notas, metas e validação."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime


class ErroValidacao(ValueError):
    """Erro de dados informado pelo usuário (vira HTTP 400/409 na API)."""


def _agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _dicts(cur) -> list[dict]:
    nomes = [d[0] for d in cur.description]
    return [dict(zip(nomes, r)) for r in cur.fetchall()]


# ============================================================ cadastros
# campo: (rótulo, tipo, obrigatório, extra)   tipo: int | float | text | sn | op | fk:<cadastro>
CADASTROS = {
    "vendedores": {
        "tabela": "vendedor", "chave": "codvend", "titulo": "Vendedores", "item": "vendedor",
        "sankhya": "TGFVEN",
        "campos": {
            "codvend": ("Código", "int", True, None), "apelido": ("Apelido", "text", True, None),
            "supervisor": ("Supervisor", "text", False, None), "gerente": ("Gerente", "text", False, None),
            "codreg": ("Região", "fk:regioes", False, None), "ativo": ("Ativo", "sn", True, None),
            "provisorio": ("Código provisório", "sn01", False, "Criado pelo sistema por não haver código no relatório"),
        },
        "lista": ["codvend", "apelido", "supervisor", "gerente", "codreg", "ativo", "provisorio"],
        "busca": ["apelido", "supervisor", "gerente"], "ordem": "apelido",
        "uso": [("nota", "codvend", "notas"), ("meta", "codvend", "metas")],
    },
    "clientes": {
        "tabela": "parceiro", "chave": "codparc", "titulo": "Clientes", "item": "cliente", "sankhya": "TGFPAR",
        "campos": {
            "codparc": ("Código", "int", True, None), "nomeparc": ("Nome / razão social", "text", True, None),
            "perfil": ("Perfil principal", "text", False, None), "cidade": ("Cidade", "text", False, None),
            "uf": ("UF", "text", False, None), "regiao_pais": ("Região do país", "text", False, None),
            "codrede": ("Cód. rede", "int", False, None), "rede": ("Rede", "text", False, None),
        },
        "lista": ["codparc", "nomeparc", "perfil", "cidade", "uf", "rede"],
        "busca": ["nomeparc", "cidade", "rede", "perfil"], "ordem": "nomeparc",
        "uso": [("nota", "codparc", "notas")],
    },
    "produtos": {
        "tabela": "produto", "chave": "codprod", "titulo": "Produtos", "item": "produto", "sankhya": "TGFPRO",
        "campos": {
            "codprod": ("Código", "int", True, None), "descrprod": ("Descrição", "text", True, None),
            "categoria": ("Categoria (metas)", "text", False, None),
            "codgrupoprod": ("Cód. conta estoque", "int", False, None), "grupoprod": ("Conta estoque", "text", False, None),
            "linha": ("Linha", "text", False, None), "familia": ("Família", "text", False, None),
            "codmix_comercial": ("Cód. mix comercial", "int", False, None), "mix_comercial": ("Mix comercial", "text", False, None),
            "codmix_biblia": ("Cód. mix bíblia", "int", False, None), "mix_biblia": ("Mix bíblia", "text", False, None),
        },
        "lista": ["codprod", "descrprod", "categoria", "grupoprod", "linha", "mix_comercial"],
        "busca": ["descrprod", "categoria", "linha", "mix_comercial"], "ordem": "descrprod",
        "uso": [("item", "codprod", "itens de nota"), ("meta", "codprod", "metas")],
    },
    "regioes": {
        "tabela": "regiao", "chave": "codreg", "titulo": "Regiões", "item": "região", "sankhya": "TSIREG",
        "campos": {"codreg": ("Código", "int", True, None), "nomereg": ("Nome", "text", True, None)},
        "lista": ["codreg", "nomereg"], "busca": ["nomereg"], "ordem": "nomereg",
        "uso": [("nota", "codreg", "notas"), ("meta", "codreg", "metas"), ("vendedor", "codreg", "vendedores")],
    },
    "tops": {
        "tabela": "tipo_operacao", "chave": "codtipoper", "titulo": "Tipos de operação (TOP)", "item": "TOP",
        "sankhya": "TGFTOP",
        "campos": {
            "codtipoper": ("Código da TOP", "int", True, None), "descroper": ("Descrição", "text", True, None),
            "operacao": ("Operação", "op", True, "V = venda, D = devolução, B = bonificação"),
        },
        "lista": ["codtipoper", "descroper", "operacao"], "busca": ["descroper"], "ordem": "codtipoper",
        "uso": [("nota", "codtipoper", "notas")],
    },
    "empresas": {
        "tabela": "empresa", "chave": "codemp", "titulo": "Empresas", "item": "empresa", "sankhya": "TSIEMP",
        "campos": {"codemp": ("Código", "int", True, None), "nomeempresa": ("Nome", "text", True, None)},
        "lista": ["codemp", "nomeempresa"], "busca": ["nomeempresa"], "ordem": "codemp",
        "uso": [("nota", "codemp", "notas")],
    },
}


def spec_publica() -> dict:
    return {k: {"titulo": c["titulo"], "item": c["item"], "chave": c["chave"], "sankhya": c["sankhya"],
                "lista": c["lista"],
                "campos": [{"campo": n, "rotulo": r, "tipo": t, "obrigatorio": o, "ajuda": x}
                           for n, (r, t, o, x) in c["campos"].items()]}
            for k, c in CADASTROS.items()}


def _cad(nome: str) -> dict:
    if nome not in CADASTROS:
        raise ErroValidacao(f"Cadastro desconhecido: {nome}")
    return CADASTROS[nome]


def _converter_campo(valor, tipo: str, rotulo: str):
    if valor is None or (isinstance(valor, str) and valor.strip() == ""):
        return None
    if tipo == "int" or tipo.startswith("fk:"):
        try:
            return int(str(valor).strip())
        except ValueError:
            raise ErroValidacao(f"{rotulo}: informe um número inteiro.")
    if tipo == "float":
        try:
            return float(str(valor).replace(",", "."))
        except ValueError:
            raise ErroValidacao(f"{rotulo}: informe um número.")
    if tipo == "sn":
        v = str(valor).strip().upper()[:1]
        if v not in ("S", "N"):
            raise ErroValidacao(f"{rotulo}: use S ou N.")
        return v
    if tipo == "sn01":
        return 1 if str(valor).strip().upper() in ("1", "S", "SIM", "TRUE") else 0
    if tipo == "op":
        v = str(valor).strip().upper()[:1]
        if v not in ("V", "D", "B"):
            raise ErroValidacao(f"{rotulo}: use V (venda), D (devolução) ou B (bonificação).")
        return v
    return str(valor).strip()


def listar_cadastro(conn, nome: str, busca: str = "", pagina: int = 0, por_pagina: int = 50) -> dict:
    c = _cad(nome)
    where, args = "", []
    if busca.strip():
        termo = f"%{busca.strip()}%"
        partes = [f"{campo} LIKE ?" for campo in c["busca"]] + [f"CAST({c['chave']} AS TEXT) LIKE ?"]
        where = "WHERE " + " OR ".join(partes)
        args = [termo] * len(partes)
    total = conn.execute(f"SELECT COUNT(*) FROM {c['tabela']} {where}", args).fetchone()[0]
    cur = conn.execute(f"SELECT * FROM {c['tabela']} {where} ORDER BY {c['ordem']} LIMIT ? OFFSET ?",
                       [*args, por_pagina, pagina * por_pagina])
    return {"total": total, "linhas": _dicts(cur)}


def opcoes_cadastro(conn, nome: str) -> list[dict]:
    """Lista curta (código + nome) para campos de seleção."""
    c = _cad(nome)
    rotulo = [k for k in c["campos"] if k != c["chave"]][0]
    cur = conn.execute(f"SELECT {c['chave']} AS codigo, {rotulo} AS nome FROM {c['tabela']} ORDER BY {rotulo}")
    return _dicts(cur)


def salvar_cadastro(conn, nome: str, dados: dict, chave_atual=None) -> dict:
    c = _cad(nome)
    valores = {}
    for campo, (rotulo, tipo, obrig, _) in c["campos"].items():
        if campo not in dados and chave_atual is not None:
            continue
        v = _converter_campo(dados.get(campo), tipo, rotulo)
        if obrig and v is None:
            raise ErroValidacao(f"{rotulo} é obrigatório.")
        if tipo.startswith("fk:") and v is not None:
            ref = CADASTROS[tipo[3:]]
            if not conn.execute(f"SELECT 1 FROM {ref['tabela']} WHERE {ref['chave']} = ?", (v,)).fetchone():
                raise ErroValidacao(f"{rotulo}: código {v} não existe em {ref['titulo'].lower()}.")
        valores[campo] = v
    if "ativo" in c["campos"] and valores.get("ativo") is None and chave_atual is None:
        valores["ativo"] = "S"
    try:
        with conn:
            if chave_atual is None:
                cols = list(valores)
                conn.execute(f"INSERT INTO {c['tabela']} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                             [valores[k] for k in cols])
            else:
                if not conn.execute(f"SELECT 1 FROM {c['tabela']} WHERE {c['chave']} = ?", (chave_atual,)).fetchone():
                    raise ErroValidacao(f"{c['item'].capitalize()} {chave_atual} não encontrado.")
                sets = ", ".join(f"{k} = ?" for k in valores)
                conn.execute(f"UPDATE {c['tabela']} SET {sets} WHERE {c['chave']} = ?", [*valores.values(), chave_atual])
    except sqlite3.IntegrityError as e:
        msg = str(e)
        if "UNIQUE" in msg or "PRIMARY KEY" in msg:
            raise ErroValidacao(f"Já existe {c['item']} com esse código ou nome.")
        raise ErroValidacao(f"Não foi possível salvar: {msg}")
    chave = valores.get(c["chave"], chave_atual)
    return _dicts(conn.execute(f"SELECT * FROM {c['tabela']} WHERE {c['chave']} = ?", (chave,)))[0]


def excluir_cadastro(conn, nome: str, chave) -> None:
    c = _cad(nome)
    usos = []
    for tabela, coluna, rotulo in c["uso"]:
        n = conn.execute(f"SELECT COUNT(*) FROM {tabela} WHERE {coluna} = ?", (chave,)).fetchone()[0]
        if n:
            usos.append(f"{n} {rotulo}")
    if usos:
        raise ErroValidacao(f"Não dá para excluir: {c['item']} usado em {', '.join(usos)}.")
    with conn:
        if not conn.execute(f"DELETE FROM {c['tabela']} WHERE {c['chave']} = ?", (chave,)).rowcount:
            raise ErroValidacao(f"{c['item'].capitalize()} {chave} não encontrado.")


# ============================================================ notas
NUNOTA_MANUAL = 900_000_000   # faixa dos Nº Únicos criados no sistema (não colide com o Sankhya)


def listar_notas(conn, periodo: str | None, busca: str = "", origem: str = "", pagina: int = 0, por_pagina: int = 50) -> dict:
    where, args = ["1=1"], []
    if periodo:
        where.append("substr(n.dtmov,1,7) = ?"); args.append(periodo)
    if origem:
        where.append("n.origem = ?"); args.append(origem)
    if busca.strip():
        t = f"%{busca.strip()}%"
        where.append("(p.nomeparc LIKE ? OR v.apelido LIKE ? OR CAST(n.nunota AS TEXT) LIKE ? OR CAST(n.numnota AS TEXT) LIKE ? OR p.cidade LIKE ?)")
        args += [t] * 5
    w = " AND ".join(where)
    base = (f"FROM nota n JOIN parceiro p ON p.codparc = n.codparc JOIN vendedor v ON v.codvend = n.codvend "
            f"JOIN tipo_operacao t ON t.codtipoper = n.codtipoper WHERE {w}")
    total, soma = conn.execute(f"SELECT COUNT(*), (SELECT COALESCE(SUM(i.vlrtot),0) FROM item i WHERE i.nunota IN (SELECT n.nunota {base})) {base}", args * 2).fetchone()
    cur = conn.execute(
        f"""SELECT n.nunota, n.numnota, n.dtmov, n.codemp, n.codtipoper, t.descroper, t.operacao, n.codparc, p.nomeparc,
                   p.cidade, p.uf, n.codvend, v.apelido AS vendedor, n.origem,
                   (SELECT COUNT(*) FROM item i WHERE i.nunota = n.nunota) AS itens,
                   (SELECT COALESCE(SUM(qtd_kg),0) FROM item i WHERE i.nunota = n.nunota) AS qtd_kg,
                   (SELECT COALESCE(SUM(vlrtot),0) FROM item i WHERE i.nunota = n.nunota) AS vlrtot
            {base} ORDER BY n.dtmov DESC, n.nunota DESC LIMIT ? OFFSET ?""", [*args, por_pagina, pagina * por_pagina])
    return {"total": total, "valor_total": soma, "linhas": _dicts(cur)}


def obter_nota(conn, nunota: int) -> dict:
    notas = _dicts(conn.execute("SELECT * FROM nota WHERE nunota = ?", (nunota,)))
    if not notas:
        raise ErroValidacao(f"Nota {nunota} não encontrada.")
    nota = notas[0]
    nota["itens"] = _dicts(conn.execute(
        "SELECT i.*, p.descrprod FROM item i JOIN produto p ON p.codprod = i.codprod WHERE nunota = ? ORDER BY sequencia", (nunota,)))
    return nota


def _existe(conn, cad: str, codigo) -> bool:
    c = CADASTROS[cad]
    return conn.execute(f"SELECT 1 FROM {c['tabela']} WHERE {c['chave']} = ?", (codigo,)).fetchone() is not None


def salvar_nota(conn, dados: dict, nunota_atual: int | None = None) -> dict:
    """Cria ou altera uma nota com seus itens.

    O usuário digita quantidades e valores positivos; o sinal é aplicado pela
    TOP (devolução e bonificação ficam negativas, como no relatório).
    """
    campos = {
        "codemp": ("Empresa", "empresas"), "codtipoper": ("TOP", "tops"), "codparc": ("Cliente", "clientes"),
        "codvend": ("Vendedor", "vendedores"),
    }
    cab = {}
    for campo, (rotulo, cad) in campos.items():
        v = _converter_campo(dados.get(campo), "int", rotulo)
        if v is None:
            raise ErroValidacao(f"{rotulo} é obrigatório.")
        if not _existe(conn, cad, v):
            raise ErroValidacao(f"{rotulo}: código {v} não cadastrado.")
        cab[campo] = v
    dt = str(dados.get("dtmov") or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", dt):
        raise ErroValidacao("Data do movimento é obrigatória (AAAA-MM-DD).")
    cab["dtmov"] = dt
    cab["numnota"] = _converter_campo(dados.get("numnota"), "int", "Nota fiscal")
    codreg = _converter_campo(dados.get("codreg"), "int", "Região")
    if codreg is None:
        codreg = conn.execute("SELECT codreg FROM vendedor WHERE codvend = ?", (cab["codvend"],)).fetchone()[0]
    elif not _existe(conn, "regioes", codreg):
        raise ErroValidacao(f"Região: código {codreg} não cadastrado.")
    cab["codreg"] = codreg
    cab["ref_rvv"] = (dados.get("ref_rvv") or "").strip() or f"{dt[5:7]}/{dt[:4]}"

    operacao = conn.execute("SELECT operacao FROM tipo_operacao WHERE codtipoper = ?", (cab["codtipoper"],)).fetchone()[0]
    sinal = -1 if operacao in ("D", "B") else 1
    itens = []
    for n, it in enumerate(dados.get("itens") or [], 1):
        codprod = _converter_campo(it.get("codprod"), "int", f"Item {n}: produto")
        if codprod is None:
            continue
        if not _existe(conn, "produtos", codprod):
            raise ErroValidacao(f"Item {n}: produto {codprod} não cadastrado.")
        kg = abs(_converter_campo(it.get("qtd_kg"), "float", f"Item {n}: quantidade") or 0)
        vlr = abs(_converter_campo(it.get("vlrtot"), "float", f"Item {n}: valor") or 0)
        st = abs(_converter_campo(it.get("vlrsubst"), "float", f"Item {n}: ST") or 0)
        if kg == 0 and vlr == 0:
            raise ErroValidacao(f"Item {n}: informe a quantidade ou o valor.")
        itens.append((codprod, sinal * kg, sinal * vlr, sinal * st, sinal * (vlr + st),
                      _converter_campo(it.get("nucte"), "int", f"Item {n}: CT-e")))
    if not itens:
        raise ErroValidacao("A nota precisa de pelo menos um item.")

    with conn:
        if nunota_atual is None:
            nunota = conn.execute("SELECT MAX(?, COALESCE(MAX(nunota), 0) + 1) FROM nota", (NUNOTA_MANUAL,)).fetchone()[0]
            conn.execute("INSERT INTO nota (nunota, numnota, codemp, dtmov, codtipoper, codparc, codvend, codreg, ref_rvv, origem) "
                         "VALUES (?,?,?,?,?,?,?,?,?, 'manual')",
                         (nunota, cab["numnota"], cab["codemp"], cab["dtmov"], cab["codtipoper"], cab["codparc"],
                          cab["codvend"], cab["codreg"], cab["ref_rvv"]))
        else:
            nunota = nunota_atual
            if not conn.execute("SELECT 1 FROM nota WHERE nunota = ?", (nunota,)).fetchone():
                raise ErroValidacao(f"Nota {nunota} não encontrada.")
            # nota importada que é editada passa a ser manual: não é apagada pela próxima importação do mês
            conn.execute("UPDATE nota SET numnota=?, codemp=?, dtmov=?, codtipoper=?, codparc=?, codvend=?, codreg=?, ref_rvv=?, "
                         "origem='manual', alterado_em=? WHERE nunota=?",
                         (cab["numnota"], cab["codemp"], cab["dtmov"], cab["codtipoper"], cab["codparc"], cab["codvend"],
                          cab["codreg"], cab["ref_rvv"], _agora(), nunota))
            conn.execute("DELETE FROM item WHERE nunota = ?", (nunota,))
        conn.executemany("INSERT INTO item (nunota, sequencia, codprod, qtd_kg, vlrtot, vlrsubst, vlrtot_st, nucte) "
                         "VALUES (?,?,?,?,?,?,?,?)", [(nunota, s, *it) for s, it in enumerate(itens, 1)])
    return obter_nota(conn, nunota)


def excluir_nota(conn, nunota: int) -> None:
    with conn:
        if not conn.execute("DELETE FROM nota WHERE nunota = ?", (nunota,)).rowcount:
            raise ErroValidacao(f"Nota {nunota} não encontrada.")


# ============================================================ metas
def listar_metas(conn, periodo: str, busca: str = "", vendedor: str = "", supervisor: str = "", gerente: str = "") -> list[dict]:
    where, args = ["periodo = ?"], [periodo]
    for col, v in (("vendedor", vendedor), ("supervisor", supervisor), ("gerente", gerente)):
        if v:
            where.append(f"{col} = ?"); args.append(v)
    if busca.strip():
        t = f"%{busca.strip()}%"
        where.append("(vendedor LIKE ? OR descrprod LIKE ? OR categoria LIKE ? OR nomereg LIKE ?)"); args += [t] * 4
    return _dicts(conn.execute(f"SELECT * FROM vw_meta WHERE {' AND '.join(where)} ORDER BY vendedor, descrprod", args))


def salvar_meta(conn, dados: dict, meta_id: int | None = None) -> dict:
    periodo = str(dados.get("periodo") or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}", periodo):
        raise ErroValidacao("Período é obrigatório (AAAA-MM).")
    codvend = _converter_campo(dados.get("codvend"), "int", "Vendedor")
    codprod = _converter_campo(dados.get("codprod"), "int", "Produto")
    codreg = _converter_campo(dados.get("codreg"), "int", "Região")
    if codvend is None or not _existe(conn, "vendedores", codvend):
        raise ErroValidacao("Vendedor é obrigatório e precisa estar cadastrado.")
    if codprod is None or not _existe(conn, "produtos", codprod):
        raise ErroValidacao("Produto é obrigatório e precisa estar cadastrado.")
    if codreg is None:
        codreg = conn.execute("SELECT codreg FROM vendedor WHERE codvend = ?", (codvend,)).fetchone()[0]
    elif not _existe(conn, "regioes", codreg):
        raise ErroValidacao(f"Região: código {codreg} não cadastrado.")
    num = {k: _converter_campo(dados.get(k), "float", r) or 0.0 for k, r in
           (("qtd_meta", "Meta (kg)"), ("pm_meta", "Preço médio da meta"), ("qtd_fechada", "Carteira (kg)"), ("vlr_fechado", "Carteira (R$)"))}
    if num["qtd_meta"] < 0 or num["pm_meta"] < 0:
        raise ErroValidacao("Meta e preço médio não podem ser negativos.")
    try:
        with conn:
            if meta_id is None:
                cur = conn.execute("INSERT INTO meta (periodo, codreg, codvend, codprod, qtd_meta, pm_meta, qtd_fechada, vlr_fechado, origem, alterado_em) "
                                   "VALUES (?,?,?,?,?,?,?,?, 'manual', ?)",
                                   (periodo, codreg, codvend, codprod, num["qtd_meta"], num["pm_meta"], num["qtd_fechada"], num["vlr_fechado"], _agora()))
                meta_id = cur.lastrowid
            else:
                n = conn.execute("UPDATE meta SET periodo=?, codreg=?, codvend=?, codprod=?, qtd_meta=?, pm_meta=?, qtd_fechada=?, vlr_fechado=?, "
                                 "origem='manual', alterado_em=? WHERE id=?",
                                 (periodo, codreg, codvend, codprod, num["qtd_meta"], num["pm_meta"], num["qtd_fechada"], num["vlr_fechado"], _agora(), meta_id)).rowcount
                if not n:
                    raise ErroValidacao(f"Meta {meta_id} não encontrada.")
    except sqlite3.IntegrityError:
        raise ErroValidacao("Já existe meta para esse vendedor, região e produto no mês.")
    return _dicts(conn.execute("SELECT * FROM vw_meta WHERE id = ?", (meta_id,)))[0]


def excluir_meta(conn, meta_id: int) -> None:
    with conn:
        if not conn.execute("DELETE FROM meta WHERE id = ?", (meta_id,)).rowcount:
            raise ErroValidacao(f"Meta {meta_id} não encontrada.")


def copiar_metas(conn, de: str, para: str) -> int:
    """Copia as metas de um mês para outro (sem carteira e sem realizado)."""
    for p in (de, para):
        if not re.fullmatch(r"\d{4}-\d{2}", p or ""):
            raise ErroValidacao("Períodos devem estar no formato AAAA-MM.")
    with conn:
        return conn.execute(
            "INSERT OR IGNORE INTO meta (periodo, codreg, codvend, codprod, qtd_meta, pm_meta, origem, alterado_em) "
            "SELECT ?, codreg, codvend, codprod, qtd_meta, pm_meta, 'manual', ? FROM meta WHERE periodo = ?",
            (para, _agora(), de)).rowcount


# ============================================================ validação
def validar(conn, periodo: str) -> list[dict]:
    """Confere a base contra os totais das planilhas importadas e regras de integridade."""
    out = []

    def add(grupo, item, esperado, obtido, estado, obs=""):
        out.append({"grupo": grupo, "item": item, "esperado": esperado, "obtido": obtido, "estado": estado, "obs": obs})

    def perto(a, b, tol=0.05):
        return a is not None and b is not None and abs(a - b) <= tol

    q = lambda sql, *a: conn.execute(sql, a).fetchone()
    for tipo, grupo in (("vendas", "Importação do demonstrativo"), ("metas", "Importação do resumo de metas")):
        carga = q("SELECT id, arquivo, emitido_em, usuario_relatorio, linhas, controle FROM carga "
                  "WHERE tipo = ? AND ',' || periodos || ',' LIKE ? ORDER BY id DESC LIMIT 1", tipo, f"%,{periodo},%")
        if not carga:
            add(grupo, "Planilha importada no mês", "sim", "não", "aviso", "Nenhuma importação deste relatório no mês.")
            continue
        cid, arquivo, emitido, usuario, linhas, controle = carga
        add(grupo, "Arquivo", "", "", "ok", f"{arquivo} · emitido em {emitido or '–'} · usuário {usuario or '–'}")
        ctl = json.loads(controle) if controle else None
        if not ctl:
            continue
        if ctl.get("total_informado") is not None:
            add(grupo, "Linhas lidas x 'Total de registros' do relatório", ctl["total_informado"], ctl["linhas"],
                "ok" if ctl["total_informado"] == ctl["linhas"] else "erro")
        if tipo == "vendas":
            n, kg, vl, st, vst, dn, dp, dprod, dv = q(
                "SELECT COUNT(*), SUM(qtd_kg), SUM(vlrtot), SUM(vlrsubst), SUM(vlrtot_st), COUNT(DISTINCT nunota), "
                "COUNT(DISTINCT codparc), COUNT(DISTINCT codprod), COUNT(DISTINCT codvend) FROM vw_venda WHERE carga_id = ?", cid)
            add(grupo, "Itens gravados na base", ctl["linhas"], n, "ok" if n == ctl["linhas"] else "aviso",
                "" if n == ctl["linhas"] else "Itens desta importação foram alterados ou excluídos depois (lançamento manual).")
            for rot, h, v in (("Soma Qtde Kg", "Qtde Kg", kg), ("Soma Valor Total Produto", "Valor Total Produto", vl),
                              ("Soma Valor ST", "Valor ST", st)):
                add(grupo, rot, round(ctl["somas"][h], 2), round(v or 0, 2), "ok" if perto(ctl["somas"][h], v or 0) else "erro")
            add(grupo, "Soma Valor Total Com ST", round(ctl["somas"]["Valor Total Com ST"], 2), round(vst or 0, 2),
                "ok" if perto(ctl["somas"]["Valor Total Com ST"], vst or 0) else "erro")
            for rot, h, v in (("Notas (Nº Único)", "Nº Único Nota", dn), ("Clientes", "Cód. Cliente", dp),
                              ("Produtos", "Cód.Produto", dprod), ("Vendedores", "Cód. Vendedor", dv)):
                add(grupo, f"{rot} distintos", ctl["distintos"][h], v, "ok" if ctl["distintos"][h] == v else "erro")
            for op, esperado in sorted(ctl["contagem"].items()):
                n_op = q("SELECT COUNT(*) FROM vw_venda WHERE carga_id = ? AND operacao = ?", cid, op)[0]
                add(grupo, f"Itens com operação {op}", esperado, n_op, "ok" if esperado == n_op else "erro")
        else:
            n, meta, fech, vfech, vend, fat, prev, dv, dp, dr = q(
                "SELECT COUNT(*), SUM(qtd_meta), SUM(qtd_fechada), SUM(vlr_fechado), SUM(vendido_rel), SUM(faturado_rel), "
                "SUM(qtd_meta * pm_meta), COUNT(DISTINCT m.codvend), COUNT(DISTINCT m.codprod), "
                "COUNT(DISTINCT COALESCE(m.codreg, -1)) FROM meta m WHERE carga_id = ?", cid)
            add(grupo, "Linhas de meta gravadas", ctl["linhas"], n, "ok" if n == ctl["linhas"] else "aviso",
                "" if n == ctl["linhas"] else "Metas desta importação foram alteradas ou excluídas depois.")
            for rot, h, v in (("Soma Meta (kg)", "Meta", meta), ("Soma Fechado (kg)", "Fechado", fech),
                              ("Soma Valor Fechado", "Valor Fechado", vfech), ("Soma Vendido do relatório", "Vendido", vend),
                              ("Soma Valor Faturado do relatório", "Valor Faturado", fat),
                              ("Valor Fat. Previsto = Meta × P.M. Meta", "Valor Fat. Previsto", prev)):
                add(grupo, rot, round(ctl["somas"][h], 2), round(v or 0, 2), "ok" if perto(ctl["somas"][h], v or 0, 0.5) else "erro")
            for rot, h, v in (("Vendedores distintos", "Vendedor", dv), ("Produtos distintos", "Cód.", dp),
                              ("Regiões distintas", "Região", dr)):
                add(grupo, rot, ctl["distintos"][h], v, "ok" if ctl["distintos"][h] == v else "erro")

    g = "Lançamentos do mês"
    nm = q("SELECT COUNT(*) FROM nota WHERE substr(dtmov,1,7) = ? AND origem = 'manual'", periodo)[0]
    mm = q("SELECT COUNT(*) FROM meta WHERE periodo = ? AND origem = 'manual'", periodo)[0]
    add(g, "Notas lançadas ou alteradas manualmente", "", nm, "ok", "Não são apagadas quando uma planilha do mês é reimportada.")
    add(g, "Metas lançadas ou alteradas manualmente", "", mm, "ok")

    g = "Integridade"
    sem_itens = q("SELECT COUNT(*) FROM nota n WHERE substr(dtmov,1,7) = ? AND NOT EXISTS (SELECT 1 FROM item i WHERE i.nunota = n.nunota)", periodo)[0]
    add(g, "Notas sem itens", 0, sem_itens, "ok" if not sem_itens else "erro")
    sinal = q("SELECT COUNT(*) FROM vw_venda WHERE periodo = ? AND ((operacao = 'V' AND vlrtot < 0) OR (operacao IN ('D','B') AND vlrtot > 0))", periodo)[0]
    add(g, "Sinal do valor coerente com a TOP", 0, sinal, "ok" if not sinal else "erro",
        "Venda positiva; devolução e bonificação negativas.")
    prov = _dicts(conn.execute("SELECT apelido FROM vendedor WHERE provisorio = 1 ORDER BY apelido"))
    add(g, "Vendedores com código provisório", 0, len(prov), "aviso" if prov else "ok",
        ("Sem código no Sankhya ainda: " + ", ".join(p["apelido"] for p in prov) + ". Ajuste em Cadastros > Vendedores.") if prov else "")

    g = "Cruzamento resumo x notas"
    r = q("SELECT SUM(vendido_rel), SUM(qtd_vendida), SUM(faturado_rel), SUM(vlr_faturado), COUNT(*), "
          "SUM(CASE WHEN ABS(vendido_rel - qtd_vendida) <= 0.01 AND ABS(faturado_rel - vlr_faturado) <= 0.05 THEN 1 ELSE 0 END) "
          "FROM vw_meta WHERE periodo = ? AND vendido_rel IS NOT NULL", periodo)
    if r and r[4]:
        kg_rel, kg, vl_rel, vl, linhas, iguais = r
        dk = (kg_rel - kg) / kg if kg else 0
        dv = (vl_rel - vl) / vl if vl else 0
        if abs(dk) > 0.10:
            add(g, "Vendido (kg): resumo x notas", round(kg_rel, 1), round(kg, 1), "erro",
                f"diferença {dk * 100:.1f}%: o resumo de metas deste mês parece ser de outro mês, ou faltam notas. "
                "Confira em Histórico (dá para trocar o mês da importação de metas).")
        else:
            add(g, "Vendido (kg): resumo x notas", round(kg_rel, 1), round(kg, 1), "ok" if abs(dk) < 0.005 else "aviso", f"diferença {dk * 100:.2f}%")
        add(g, "Faturado (R$): resumo x notas", round(vl_rel, 2), round(vl, 2), "ok" if abs(dv) < 0.005 else "aviso", f"diferença {dv * 100:.2f}%")
        add(g, "Linhas de meta com realizado idêntico", linhas, iguais, "ok" if iguais == linhas else "aviso",
            "" if iguais == linhas else "As diferenças por linha estão em Dados > Conciliação.")
    return out
