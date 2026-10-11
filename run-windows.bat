@echo off
rem Inicia a API e o Metro do VisualMatch no Windows (equivalente ao run-macos.sh).
rem A logica fica em run-windows.ps1; a ExecutionPolicy e liberada so para esta execucao.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-windows.ps1"
set "EXIT_CODE=%ERRORLEVEL%"
rem Codigo 2 = erro de configuracao: mantem a janela aberta para quem abriu com duplo clique.
if "%EXIT_CODE%"=="2" pause
exit /b %EXIT_CODE%
