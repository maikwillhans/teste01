"""Importa planilhas pela linha de comando (útil para agendar).

    python scripts/importar.py arquivo1.xls [arquivo2.xls ...] [--periodo-meta 2026-09] [--forcar]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vendas_bi.db import conectar  # noqa: E402
from vendas_bi.importer import ErroImportacao, importar  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("arquivos", nargs="+")
ap.add_argument("--periodo-meta", help="mês das metas, AAAA-MM (padrão: mês da emissão)")
ap.add_argument("--forcar", action="store_true", help="reimporta mesmo arquivo idêntico")
ap.add_argument("--banco", help="caminho da base SQLite")
args = ap.parse_args()

conn = conectar(args.banco)
erro = False
# demonstrativo antes: o mês do resumo de metas é identificado pelas vendas
for arq in sorted(args.arquivos, key=lambda a: "metas" in a.lower()):
    try:
        r = importar(conn, arq, periodo_meta=args.periodo_meta, forcar=args.forcar)
    except ErroImportacao as e:
        print(f"ERRO {arq}: {e}")
        erro = True
        continue
    estado = "ignorado (já importado)" if r.ignorada else f"{r.linhas} linhas, {r.substituidas} substituídas"
    print(f"OK   {arq}: {r.tipo} {','.join(r.periodos)} - {estado}")
    for aviso in r.avisos:
        print(f"     aviso: {aviso}")
sys.exit(1 if erro else 0)
