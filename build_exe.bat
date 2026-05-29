@echo off
REM Buduje jeden plik dist\AIQuizGenerator.exe
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo Brak .venv — uruchom: python -m venv .venv
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
pip install -r requirements.txt pyinstaller

pyinstaller --noconfirm --clean AIQuizGenerator.spec

echo.
echo Gotowe: dist\AIQuizGenerator.exe
echo Skopiuj obok exe plik .env z kluczem GROQ_API_KEY
echo.
pause
