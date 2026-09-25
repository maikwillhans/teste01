"""Layouts dos relatórios exportados e o de-para para as colunas da base.

Cada relatório tem:
  - ``titulo``: texto da célula A1, usado para detectar o tipo do arquivo;
  - ``colunas``: cabeçalho do relatório -> (coluna na base, tipo, campo Sankhya).

O nome das colunas da base segue, sempre que existe equivalente, o nome do
campo no dicionário do Sankhya (TGFCAB, TGFITE, TGFPRO, TGFPAR, TGFVEN...).
Assim, quando a carga passar a vir direto do Sankhya, basta a consulta SQL
devolver as mesmas colunas (ver ``vendas_bi/sankhya/``).

Tipos: ``str``, ``int``, ``float``, ``date`` (dd/mm/aaaa).

A coluna ``regiao`` ("101003026 - ZV131 - VILMAR") é separada pelo importador
em ``codreg`` (101003026) e ``nomereg`` ("ZV131 - VILMAR").
"""

VENDAS = "vendas"
METAS = "metas"

LAYOUTS = {
    VENDAS: {
        "titulo": "Demonstrativo Mensal das Vendas Efetuadas",
        "tabela": "fato_venda",
        "colunas": {
            # cabeçalho do relatório : (coluna, tipo, origem no Sankhya)
            "Ano": (None, "str", "derivado de DTMOV"),
            "Mês": (None, "str", "derivado de DTMOV"),
            "Dia": (None, "str", "derivado de DTMOV"),
            "Perfil Principal": ("perfil", "str", "TGFPPA/TGFPER - perfil principal do parceiro"),
            "Região": ("regiao", "str", "TSIREG.CODREG + NOMEREG"),
            "Nota Fiscal": ("numnota", "int", "TGFCAB.NUMNOTA"),
            "Gerente": ("gerente", "str", "TGFVEN.APELIDO (via TGFVEN.CODGER)"),
            "Empresa": ("codemp", "int", "TGFCAB.CODEMP"),
            "Supervisor": ("supervisor", "str", "TGFVEN.APELIDO (supervisor)"),
            "Vendedor": ("vendedor", "str", "TGFVEN.APELIDO"),
            "Cód. Cliente": ("codparc", "int", "TGFCAB.CODPARC"),
            "Cliente": ("nomeparc", "str", "TGFPAR.NOMEPARC"),
            "Cidade": ("cidade", "str", "TSICID.NOMECID"),
            "Uf": ("uf", "str", "TSIUFS.UF"),
            "Cód.Produto": ("codprod", "int", "TGFITE.CODPROD"),
            "Descrição Produto": ("descrprod", "str", "TGFPRO.DESCRPROD"),
            "Cód.Conta": ("codgrupoprod", "int", "TGFPRO.CODGRUPOPROD"),
            "Conta Estoque": ("grupoprod", "str", "TGFGRU.DESCRGRUPOPROD"),
            "Qtde Kg": ("qtd_kg", "float", "TGFITE.QTDNEG x peso (TGFPRO.PESOLIQ)"),
            "Valor Total Produto": ("vlrtot", "float", "TGFITE.VLRTOT"),
            "Data Mvto": ("dtmov", "date", "TGFCAB.DTMOV"),
            # lido só para validação (a base recalcula vlrtot / qtd_kg)
            "Preço Médio": ("preco_medio_rel", "float", "derivado: vlrtot / qtd_kg"),
            "Valor Total Com ST": ("vlrtot_st", "float", "TGFITE.VLRTOT + VLRSUBST"),
            "Valor ST": ("vlrsubst", "float", "TGFITE.VLRSUBST"),
            "Linha": ("linha", "str", "campo adicional do produto (AD_LINHA)"),
            "TOP": ("codtipoper", "int", "TGFCAB.CODTIPOPER"),
            "Nome da TOP": ("descroper", "str", "TGFTOP.DESCROPER"),
            "Nome Família": ("familia", "str", "campo adicional do produto"),
            "Operação": ("operacao", "str", "V=venda, D=devolução, B=bonificação (regra da TOP)"),
            "Cód Mix Comercial": ("codmix_comercial", "int", "campo adicional do produto"),
            "Mix Comercial": ("mix_comercial", "str", "campo adicional do produto"),
            "Cód Mix Bíblia": ("codmix_biblia", "int", "campo adicional do produto"),
            "Mix Bíblia": ("mix_biblia", "str", "campo adicional do produto"),
            "Cód. Rede": ("codrede", "int", "campo adicional do parceiro"),
            "Cód. Vendedor": ("codvend", "int", "TGFCAB.CODVEND"),
            "Nº CTE": ("nucte", "int", "NUNOTA do CT-e vinculado"),
            "Nº Único Nota": ("nunota", "int", "TGFCAB.NUNOTA"),
            "Rede": ("rede", "str", "campo adicional do parceiro"),
            "Região País": ("regiao_pais", "str", "TSIUFS -> região do país"),
            "Ref. RVV": ("ref_rvv", "str", "mês de referência (MM/AAAA)"),
        },
        "obrigatorias": ["Nº Único Nota", "Cód.Produto", "Data Mvto", "Valor Total Produto"],
    },
    METAS: {
        "titulo": "RESUMO GERAL DAS METAS/VENDAS",
        "tabela": "fato_meta",
        "colunas": {
            "Vendedor Ativo?": ("vendedor_ativo", "str", "TGFVEN.ATIVO"),
            "Gerente": ("gerente", "str", "TGFVEN.APELIDO (gerente)"),
            "Supervisor": ("supervisor", "str", "TGFVEN.APELIDO (supervisor)"),
            "Região": ("regiao", "str", "TSIREG.CODREG + NOMEREG"),
            "Vendedor": ("vendedor", "str", "TGFVEN.APELIDO"),
            "Categoria": ("categoria", "str", "Mix Comercial do produto"),
            "Cód.": ("codprod", "int", "TGFMET.CODPROD"),
            "Produto": ("descrprod", "str", "TGFPRO.DESCRPROD"),
            "Vendido": ("qtd_vendida", "float", "realizado em kg (vendas - devoluções)"),
            "Meta": ("qtd_meta", "float", "TGFMET.QTDPREV (kg)"),
            "Fechado": ("qtd_fechada", "float", "pedidos em carteira, kg (TGFCAB TIPMOV=P pendente)"),
            "Valor Fechado": ("vlr_fechado", "float", "pedidos em carteira, R$"),
            "P.M. Meta": ("pm_meta", "float", "preço médio da meta (R$/kg)"),
            # Os campos abaixo são calculados. O valor do relatório é lido como *_rel
            # só para validação; a base recalcula na view vw_meta.
            "% Meta": ("perc_meta_rel", "float", "derivado: qtd_vendida / qtd_meta"),
            "% Prev.": ("perc_prev_rel", "float", "derivado: (qtd_vendida + qtd_fechada) / qtd_meta"),
            "Diferença": ("diferenca_rel", "float", "derivado: qtd_meta - qtd_vendida"),
            "P.M. Real.": ("pm_real_rel", "float", "derivado: vlr_faturado / qtd_vendida"),
            "Prévia": ("previa_rel", "float", "derivado: qtd_meta - qtd_vendida - qtd_fechada"),
            "Valor Faturado": ("vlr_faturado", "float", "realizado em R$"),
            "Valor Fat. Previsto": ("vlr_previsto_rel", "float", "derivado: qtd_meta * pm_meta"),
        },
        "obrigatorias": ["Vendedor", "Cód.", "Meta", "Vendido"],
    },
}


def colunas_base(tipo: str) -> list[str]:
    """Colunas lidas do relatório (antes de separar ``regiao``)."""
    return [c for c, _, _ in LAYOUTS[tipo]["colunas"].values() if c]
