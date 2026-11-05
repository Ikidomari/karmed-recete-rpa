@echo off
chcp 65001 >nul
echo ========================================================
echo   Karmed ^& Recetem Otomasyonu - EXE ve Updater Derleyici
echo ========================================================
echo.

echo [1/4] Gerekli kutuphaneler (requests, playwright, pyinstaller) kontrol ediliyor...
python -m pip install -r requirements.txt

echo.
echo [2/4] Ana Uygulama (ReceteOtomasyon.exe) derleniyor...
python -m PyInstaller --noconfirm --onefile --noconsole ^
    --name "ReceteOtomasyon" ^
    --collect-all playwright ^
    --hidden-import dotenv ^
    gui_app.py

echo.
echo [3/4] Auto-Updater (Updater.exe) konsolsuz olarak derleniyor...
python -m PyInstaller --noconfirm --onefile --noconsole ^
    --name "Updater" ^
    updater.py

echo.
echo [4/4] Yapilandirma dosyalari dist klasorune kopyalaniyor...
if exist ".env" (
    copy /Y ".env" "dist\.env" >nul
) else (
    copy /Y ".env.example" "dist\.env" >nul
)
if exist "selectors.json" (
    copy /Y "selectors.json" "dist\selectors.json" >nul
)
if exist "local_version.txt" (
    copy /Y "local_version.txt" "dist\local_version.txt" >nul
)
if exist "GEMINI_HASTANE_REHBERI.md" (
    copy /Y "GEMINI_HASTANE_REHBERI.md" "dist\GEMINI_HASTANE_REHBERI.md" >nul
)

echo.
echo ========================================================
echo   ISLEM TAMAMLANDI!
echo   Olusturulan dosyalar "dist" klasoru icindedir:
echo     - dist\Updater.exe          (Kullanicilarin tiklayacagi guncelleyici)
echo     - dist\ReceteOtomasyon.exe  (Ana RPA uygulamasi)
echo     - dist\local_version.txt
echo     - dist\.env
echo     - dist\selectors.json
echo ========================================================
pause
