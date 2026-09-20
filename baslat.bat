@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0baslat.py" %*
  goto :son
)

where python >nul 2>nul
if %errorlevel%==0 (
  python "%~dp0baslat.py" %*
  goto :son
)

echo.
echo Python 3 bulunamadi.
echo Kurulum: https://www.python.org/downloads/
echo Kurulumda "Add python.exe to PATH" secenegini isaretleyin.
echo.

:son
if "%~1"=="" pause
endlocal
