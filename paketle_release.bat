@echo off
chcp 65001 >nul
echo ========================================================
echo   GitHub Release Paketi (app.zip) Hazirlayici
echo ========================================================
echo.

echo [1/4] Kutuphaneler kontrol ediliyor...
python -m pip install -r requirements.txt

echo.
echo [2/4] ReceteOtomasyon_v1_1.exe derleniyor...
python -m PyInstaller --noconfirm --onefile --noconsole ^
    --name "ReceteOtomasyon_v1_1" ^
    --collect-all playwright ^
    --hidden-import dotenv ^
    --hidden-import requests ^
    gui_app_v1_1.py

echo.
echo [3/4] Release klasoru hazirlaniyor (.env HARIC tutuluyor)...
if exist "release_paketi" rmdir /S /Q "release_paketi"
mkdir "release_paketi\icerik"

copy /Y "dist\ReceteOtomasyon_v1_1.exe" "release_paketi\icerik\ReceteOtomasyon_v1_1.exe" >nul
copy /Y "selectors.json" "release_paketi\icerik\selectors.json" >nul
copy /Y "local_version.txt" "release_paketi\icerik\local_version.txt" >nul
copy /Y ".env.example" "release_paketi\icerik\.env.example" >nul

echo.
echo [4/4] GitHub Releases icin app.zip olusturuluyor...
powershell -NoProfile -Command "Compress-Archive -Path 'release_paketi\icerik\*' -DestinationPath 'release_paketi\app.zip' -Force"

echo.
echo ========================================================
echo   ISLEM TAMAMLANDI!
echo   GitHub Release'e yukleyeceginiz dosya hazir:
echo     - release_paketi\app.zip
echo ========================================================
pause

