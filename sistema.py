"""Inicia o Sistema Vendas x Metas.

    python sistema.py            -> http://localhost:8000
    python sistema.py --porta 8080 --banco data/outra.db
"""

import argparse
import os
import socket
import webbrowser

import uvicorn

ap = argparse.ArgumentParser(description="Sistema Vendas x Metas")
ap.add_argument("--porta", type=int, default=8000)
ap.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 para acessar de outros computadores da rede")
ap.add_argument("--rede", action="store_true", help="libera o acesso de outros computadores da rede (= --host 0.0.0.0)")
ap.add_argument("--banco", help="arquivo SQLite (padrão: data/sistema.db)")
ap.add_argument("--sem-navegador", action="store_true")
args = ap.parse_args()
if args.rede:
    args.host = "0.0.0.0"


def enderecos_na_rede() -> list[str]:
    """IPs deste computador na rede local, para informar aos outros usuários."""
    ips = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))   # não envia nada; só descobre a interface de saída
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    try:
        ips.update(ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127."))
    except OSError:
        pass
    return sorted(ips)


if args.banco:
    os.environ["VENDAS_BI_DB"] = args.banco

from vendas_bi.api import criar_app  # noqa: E402  (depois de definir o banco)

app = criar_app(args.banco)
if not args.sem_navegador:
    webbrowser.open(f"http://localhost:{args.porta}")
print()
print(f"  Neste computador:   http://localhost:{args.porta}")
if args.host == "0.0.0.0":
    for ip in enderecos_na_rede():
        print(f"  Outros computadores: http://{ip}:{args.porta}")
else:
    print("  Acesso só deste computador. Para liberar a rede use iniciar_rede.bat ou --rede.")
print()
uvicorn.run(app, host=args.host, port=args.porta)
