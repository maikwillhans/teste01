@echo off
title Sistema Vendas x Metas (rede)
cd /d "%~dp0"

rem Libera a porta 8000 no Firewall do Windows (so precisa de administrador na primeira vez)
netsh advfirewall firewall show rule name="Sistema Vendas x Metas" >nul 2>nul
if errorlevel 1 (
  net session >nul 2>nul
  if errorlevel 1 (
    echo.
    echo Na primeira vez e preciso liberar o firewall.
    echo Clique com o botao direito em iniciar_rede.bat e escolha "Executar como administrador".
    echo.
    pause
    exit /b 1
  )
  netsh advfirewall firewall add rule name="Sistema Vendas x Metas" dir=in action=allow protocol=TCP localport=8000 profile=domain,private >nul
  echo Firewall liberado para a porta 8000 nas redes privadas e de dominio.
)

where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale em https://www.python.org/downloads/ marcando "Add python.exe to PATH".
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
echo Deixe esta janela aberta. Os outros computadores usam o endereco "Outros computadores" abaixo.
python sistema.py --rede
pause
