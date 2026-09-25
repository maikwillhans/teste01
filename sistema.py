"""Inicia o Sistema Vendas x Metas.

    python sistema.py            -> http://localhost:8000
    python sistema.py --porta 8080 --banco data/outra.db
"""

import argparse
import os
import webbrowser

import uvicorn

ap = argparse.ArgumentParser(description="Sistema Vendas x Metas")
ap.add_argument("--porta", type=int, default=8000)
ap.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 para acessar de outros computadores da rede")
ap.add_argument("--banco", help="arquivo SQLite (padrão: data/sistema.db)")
ap.add_argument("--sem-navegador", action="store_true")
args = ap.parse_args()

if args.banco:
    os.environ["VENDAS_BI_DB"] = args.banco

from vendas_bi.api import criar_app  # noqa: E402  (depois de definir o banco)

app = criar_app(args.banco)
if not args.sem_navegador:
    webbrowser.open(f"http://localhost:{args.porta}")
uvicorn.run(app, host=args.host, port=args.porta)
