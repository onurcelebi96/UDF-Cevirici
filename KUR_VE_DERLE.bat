@echo off
title UDF Cevirici - EXE Olusturucu
echo.
echo ===================================================
echo    UDF Cevirici - Otomatik EXE Olusturucu
echo    Gelistirici: Onur Celebi
echo ===================================================
echo.
echo Hicbir sey yuklemeden otomatik EXE olusturulacak.
echo Lutfen bekleyin...
echo.

set "PYVER=3.11.9"
set "PYZIP=python-%PYVER%-embed-amd64.zip"
set "PYURL=https://www.python.org/ftp/python/%PYVER%/%PYZIP%"
set "PYDIR=%~dp0_portable_python"
set "PIPURL=https://bootstrap.pypa.io/get-pip.py"

REM -----------------------------------------------
REM 1) Portable Python indir
REM -----------------------------------------------
echo [1/5] Portable Python indiriliyor...
if exist "%PYDIR%" rmdir /s /q "%PYDIR%"
mkdir "%PYDIR%"

powershell -Command "Invoke-WebRequest -Uri '%PYURL%' -OutFile '%PYDIR%\python.zip'" 2>nul
if errorlevel 1 (
    certutil -urlcache -split -f "%PYURL%" "%PYDIR%\python.zip" >nul 2>&1
)
if not exist "%PYDIR%\python.zip" (
    echo HATA: Python indirilemedi. Internet baglantinizi kontrol edin.
    pause
    exit /b 1
)
echo       Python indirildi.

REM -----------------------------------------------
REM 2) Python zip'i cikar ve pip kur
REM -----------------------------------------------
echo [2/5] Python hazirlaniyor...
powershell -Command "Expand-Archive -Path '%PYDIR%\python.zip' -DestinationPath '%PYDIR%' -Force"
del /f /q "%PYDIR%\python.zip" 2>nul

REM Enable pip in embedded python (remove _pth restriction)
for %%f in ("%PYDIR%\python*._pth") do (
    echo import site>> "%%f"
)

REM Download get-pip.py
powershell -Command "Invoke-WebRequest -Uri '%PIPURL%' -OutFile '%PYDIR%\get-pip.py'" 2>nul
if errorlevel 1 (
    certutil -urlcache -split -f "%PIPURL%" "%PYDIR%\get-pip.py" >nul 2>&1
)

REM Install pip
"%PYDIR%\python.exe" "%PYDIR%\get-pip.py" --no-warn-script-location >nul 2>&1
echo       Python ve pip hazir.

REM -----------------------------------------------
REM 3) Kutuphaneleri yukle
REM -----------------------------------------------
echo [3/5] Kutuphaneler yukleniyor...
"%PYDIR%\python.exe" -m pip install --no-warn-script-location --quiet python-docx
"%PYDIR%\python.exe" -m pip install --no-warn-script-location --quiet PyMuPDF
"%PYDIR%\python.exe" -m pip install --no-warn-script-location --quiet Pillow
"%PYDIR%\python.exe" -m pip install --no-warn-script-location --quiet reportlab
"%PYDIR%\python.exe" -m pip install --no-warn-script-location --quiet pyinstaller
echo       Kutuphaneler yuklendi.

REM -----------------------------------------------
REM 4) EXE olustur
REM -----------------------------------------------
echo [4/5] EXE olusturuluyor (2-5 dakika surebilir)...
if exist "%~dp0build" rmdir /s /q "%~dp0build"
if exist "%~dp0dist" rmdir /s /q "%~dp0dist"

"%PYDIR%\Scripts\pyinstaller.exe" --noconfirm --onefile --windowed --clean --name "UDF-Cevirici" --add-data "udf_to_docx.py;." --add-data "udf_to_pdf.py;." --add-data "docx_to_udf.py;." --add-data "scanned_pdf_to_udf.py;." --add-data "main.py;." --add-data "paragraph_processor.py;." --add-data "table_processor.py;." --add-data "image_processor.py;." --add-data "utils.py;." --exclude-module numpy --exclude-module pandas --exclude-module matplotlib --exclude-module scipy --exclude-module PyQt5 --exclude-module PyQt6 --exclude-module IPython --exclude-module pytest --distpath "%~dp0dist" --workpath "%~dp0build" --specpath "%~dp0" gui_app.py

if not exist "%~dp0dist\UDF-Cevirici.exe" (
    echo.
    echo HATA: EXE olusturulamadi!
    pause
    exit /b 1
)
echo       EXE basariyla olusturuldu!

REM -----------------------------------------------
REM 5) Temizlik
REM -----------------------------------------------
echo [5/5] Gecici dosyalar temizleniyor...
rmdir /s /q "%PYDIR%" 2>nul
rmdir /s /q "%~dp0build" 2>nul
del /f /q "%~dp0UDF-Cevirici.spec" 2>nul

echo.
echo ===================================================
echo    TAMAMLANDI!
echo.
echo    UDF-Cevirici.exe dosyaniz hazir:
echo    %~dp0dist\UDF-Cevirici.exe
echo.
echo    Bu dosya tek basina calisir.
echo    Python veya baska bir programa ihtiyac duymaz.
echo    Istediginiz bilgisayara kopyalayabilirsiniz.
echo ===================================================
echo.

explorer "%~dp0dist"
pause
