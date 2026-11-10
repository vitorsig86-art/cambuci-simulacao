@echo off
call "C:\Program Files\QGIS 3.44.13\bin\o4w_env.bat" >nul 2>&1
set PYTHONIOENCODING=utf-8
set PYTHONDONTWRITEBYTECODE=1
python %*
