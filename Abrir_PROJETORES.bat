@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Ambiente virtual nao encontrado em .venv
  echo.
  echo Execute uma vez:
  echo python -m venv .venv
  echo .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)

start "PROJETORES" /D "%~dp0" cmd /k ".venv\Scripts\python.exe app.py"

for /L %%I in (1,1,10) do (
  powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:5001/login' -UseBasicParsing -TimeoutSec 2 > $null; exit 0 } catch { exit 1 }"
  if not errorlevel 1 goto abrir_navegador
  timeout /t 1 /nobreak >nul
)

echo O servidor nao respondeu em ate 10 segundos.
echo Confira a janela "PROJETORES" para ver se apareceu algum erro.
pause
exit /b 1

:abrir_navegador
start "" "http://127.0.0.1:5001/login"
