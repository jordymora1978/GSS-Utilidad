@echo off
title Sistema Contable Multipais
echo ================================================
echo SISTEMA CONTABLE MULTIPAIS - STREAMLIT
echo ================================================
echo IMPORTANTE: Ejecutar como ADMINISTRADOR
echo ================================================

cd /d "%~dp0"

echo.
echo Iniciando sistema contable en http://localhost:8501...
echo.
echo Funcionalidades disponibles:
echo   - Gestion financiera Colombia, Peru, Chile
echo   - Analisis de datos con graficos
echo   - Exportacion a Excel
echo   - Dashboard interactivo
echo.
echo Presiona Ctrl+C para detener el servidor
echo ================================================

python -m streamlit run streamlit_app.py --server.headless=true --server.port=8501