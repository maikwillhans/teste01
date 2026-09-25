@echo off
title Sistema Vendas x Metas
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo Python nao encontrado.
  echo Instale em https://www.python.org/downloads/ e marque a opcao "Add python.exe to PATH".
  echo Depois feche esta janela e clique de novo em iniciar.bat.
  echo.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Preparando o sistema pela primeira vez, aguarde alguns minutos...
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"
python -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
  echo Nao foi possivel instalar os componentes. Verifique a internet e tente de novo.
  pause
  exit /b 1
)

echo.
echo Sistema no ar em http://localhost:8000
echo Deixe esta janela aberta enquanto usa o sistema. Para encerrar, feche a janela.
echo.
python sistema.py
pause
