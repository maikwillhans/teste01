"""Gera o painel HTML já com os dados reais das planilhas embutidos.

    python scripts/gerar_dashboard.py data/Demonstrativo*.xls data/RESUMO*.xls
    -> data/painel_vendas_metas.html  (fora do git: contém dados de clientes)

Os dados são lidos pelo mesmo importador da base (vendas_bi.importer). Além
disso, cada planilha é relida célula a célula com xlrd, de forma
independente, para gerar os totais de controle (linhas, somas por coluna,
distintos). A página "Validação" do painel confere os dados carregados
contra esses totais e contra as fórmulas do próprio relatório.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from vendas_bi.importer import ler_relatorio  # noqa: E402
from vendas_bi.layouts import LAYOUTS  # noqa: E402

MARCA = '<script type="application/json" id="dados-embutidos">null</script>'

CONTROLE = {
    "vendas": {
        "somas": ["Qtde Kg", "Valor Total Produto", "Valor Total Com ST", "Valor ST"],
        "distintos": ["Nº Único Nota", "Cód. Cliente", "Cód.Produto", "Cód. Vendedor", "Cidade", "Uf"],
        "contagem": "Operação",
    },
    "metas": {
        "somas": ["Vendido", "Meta", "Fechado", "Valor Fechado", "Valor Faturado", "Valor Fat. Previsto",
                  "Diferença", "Prévia"],
        "distintos": ["Vendedor", "Cód.", "Região", "Supervisor"],
        "contagem": "Categoria",
    },
}


def controle_bruto(caminho: Path, tipo: str) -> dict:
    """Totais lidos direto das células, sem passar pelo importador."""
    import xlrd

    folha = xlrd.open_workbook(str(caminho)).sheet_by_index(0)
    obrig = LAYOUTS[tipo]["obrigatorias"]
    for i in range(min(15, folha.nrows)):
        cab = [str(v).strip() for v in folha.row_values(i)]
        if set(obrig) <= set(cab):
            break
    else:
        raise SystemExit(f"{caminho.name}: cabeçalho não encontrado")
    col = {c: j for j, c in enumerate(cab)}
    chave = col[obrig[0]]
    topo = " ".join(str(v) for r in range(i) for v in folha.row_values(r))
    total = None
    if "Total de registros:" in topo:
        total = int(topo.split("Total de registros:")[1].split()[0])

    cfg = CONTROLE[tipo]
    somas = {c: 0.0 for c in cfg["somas"]}
    distintos = {c: set() for c in cfg["distintos"]}
    contagem: dict[str, int] = {}
    linhas = 0
    for r in range(i + 1, folha.nrows):
        v = folha.row_values(r)
        if str(v[chave]).strip() == "":
            continue
        linhas += 1
        for c in somas:
            x = v[col[c]]
            somas[c] += float(x) if x not in ("", None) else 0.0
        for c in distintos:
            x = v[col[c]]
            if x not in ("", None):
                distintos[c].add(x)
        k = str(v[col[cfg["contagem"]]]).strip()
        contagem[k] = contagem.get(k, 0) + 1
    return {
        "linhas": linhas, "total_informado": total,
        "somas": {c: round(s, 4) for c, s in somas.items()},
        "distintos": {c: len(s) for c, s in distintos.items()},
        "contagem_campo": cfg["contagem"], "contagem": contagem,
    }


def colunar(df: pd.DataFrame) -> dict:
    """Formato compacto: texto vira dicionário + índices; número fica como lista."""
    out = {"n": len(df), "cols": {}}
    for c in df.columns:
        s = df[c]
        if not pd.api.types.is_numeric_dtype(s):
            valores = s.where(s.notna(), None).tolist()
            dic = sorted({v for v in valores if v is not None})
            pos = {v: k for k, v in enumerate(dic)}
            out["cols"][c] = {"d": dic, "i": [pos[v] if v is not None else -1 for v in valores]}
        else:
            out["cols"][c] = {"v": [None if pd.isna(v) else (int(v) if float(v).is_integer() and "Int" in str(s.dtype) else round(float(v), 6)) for v in s]}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("arquivos", nargs="+")
    ap.add_argument("--modelo", default=str(RAIZ / "dashboard.html"))
    ap.add_argument("--saida", default=str(RAIZ / "data" / "painel_vendas_metas.html"))
    ap.add_argument("--periodo-meta")
    args = ap.parse_args()

    dados = {"gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"), "cargas": [], "vendas": None, "metas": None}
    tabelas = {}
    for n, arq in enumerate(args.arquivos, 1):
        caminho = Path(arq)
        conteudo = caminho.read_bytes()
        rel = ler_relatorio(conteudo, caminho.name, args.periodo_meta, todas=True)
        if rel.tipo in tabelas:
            tabelas[rel.tipo] = pd.concat([tabelas[rel.tipo], rel.dados], ignore_index=True)
        else:
            tabelas[rel.tipo] = rel.dados
        ctl = controle_bruto(caminho, rel.tipo)
        dados["cargas"].append({
            "id": n, "tipo": rel.tipo, "origem": "planilha (embutida)", "arquivo": caminho.name,
            "sha256": hashlib.sha256(conteudo).hexdigest(), "periodos": rel.periodos, "linhas": len(rel.dados),
            "emitido_em": rel.emitido_em.strftime("%Y-%m-%d %H:%M:%S") if rel.emitido_em else None,
            "usuario_relatorio": rel.usuario, "importado_em": dados["gerado_em"], "controle": ctl,
        })
        print(f"{caminho.name}: {rel.tipo} {','.join(rel.periodos)} - {len(rel.dados)} linhas "
              f"(controle: {ctl['linhas']} linhas, informado {ctl['total_informado']})")

    # código do vendedor no resumo de metas, pelo apelido no demonstrativo
    if "metas" in tabelas:
        m = tabelas["metas"]
        mapa = {}
        if "vendas" in tabelas:
            v = tabelas["vendas"].dropna(subset=["codvend"])
            mapa = v.groupby("vendedor")["codvend"].agg(lambda s: s.mode().iloc[0]).to_dict()
        m["codvend"] = m["vendedor"].map(mapa).astype("Int64")
    for tipo, df in tabelas.items():
        dados[tipo] = colunar(df)

    js = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    modelo = Path(args.modelo).read_text(encoding="utf-8")
    if MARCA not in modelo:
        raise SystemExit("Marcador de dados não encontrado no modelo.")
    saida = Path(args.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(modelo.replace(MARCA, f'<script type="application/json" id="dados-embutidos">{js}</script>'),
                     encoding="utf-8")
    print(f"-> {saida} ({saida.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
