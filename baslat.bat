@echo off
chcp 65001 >nul
title Kayseri Gayrimenkul Degerleme Platformu
cd /d "%~dp0"
echo ================================================
echo  Kayseri Gayrimenkul Degerleme Platformu baslatiliyor...
echo ================================================
echo.
py -m streamlit run app.py
pause
