@echo off
setlocal
cd /d "%~dp0"

echo ================================================================
echo Question Bank Cleaner - build portavel para Windows
echo ================================================================

where py >nul 2>nul
if errorlevel 1 (
    echo ERRO: Python nao foi encontrado pelo comando "py".
    echo Instale Python 3.11 ou superior e tente novamente.
    pause
    exit /b 1
)

if not exist ".venv-build" (
    py -m venv .venv-build
)

call .venv-build\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt

set "ICON_ARGS="
if exist "assets\question_bank_cleaner.ico" (
    set "ICON_ARGS=%ICON_ARGS% --icon=assets\question_bank_cleaner.ico --add-data=assets\question_bank_cleaner.ico;assets"
)
if exist "assets\question_bank_cleaner.png" (
    set "ICON_ARGS=%ICON_ARGS% --add-data=assets\question_bank_cleaner.png;assets"
)

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name QuestionBankCleaner ^
    %ICON_ARGS% ^
    app.py

if errorlevel 1 (
    echo.
    echo O build falhou. Verifique as mensagens acima.
    pause
    exit /b 1
)

echo.
echo Build concluido.
echo Executavel: dist\QuestionBankCleaner.exe
if exist "assets\question_bank_cleaner.ico" (
    echo Icone personalizado incorporado.
) else (
    echo AVISO: nenhum assets\question_bank_cleaner.ico foi encontrado.
)
echo.
pause
