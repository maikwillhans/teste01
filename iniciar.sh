#!/usr/bin/env bash
# Inicia o Sistema Vendas x Metas (Mac/Linux). Uso: ./iniciar.sh
set -e
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null; then
  echo "Python 3 não encontrado. Instale em https://www.python.org/downloads/"; exit 1
fi
if [ ! -x .venv/bin/python ]; then
  echo "Preparando o sistema pela primeira vez, aguarde alguns minutos..."
  python3 -m venv .venv
fi
. .venv/bin/activate
python -m pip install --disable-pip-version-check -q -r requirements.txt
echo
echo "Sistema no ar em http://localhost:8000 — deixe este terminal aberto. Ctrl+C encerra."
echo
python sistema.py "$@"
