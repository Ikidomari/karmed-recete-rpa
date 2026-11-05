@echo off
chcp 65001 >nul
echo ========================================================
echo   Karmed ^& Recetem Otomasyonu - v1.1 Deneme Derleyici
echo ========================================================
echo.

python -m pip install -r requirements.txt

echo.
echo ReceteOtomasyon_v1_1.exe derleniyor...
python -m PyInstaller --noconfirm --onefile --noconsole ^
    --name "ReceteOtomasyon_v1_1" ^
    --collect-all playwright ^
    --hidden-import dotenv ^
    --hidden-import requests ^
    gui_app_v1_1.py

echo.
echo ========================================================
echo   ISLEM TAMAMLANDI!
echo   dist\ReceteOtomasyon_v1_1.exe olusturuldu.
echo   (Mevcut ReceteOtomasyon.exe dosyaniza dokunulmadi!)
echo ========================================================
pause

