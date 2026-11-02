@echo off
rem publicar.bat - publicar con doble clic.
rem
rem Corre publicar.ps1: trae de GitHub lo corregido desde el telefono,
rem rehace los datos de la app con todas las erratas puestas y lo sube, y
rem GitHub Pages lo publica en un par de minutos.
rem
rem Es un .bat porque Windows no deja correr los .ps1 con doble clic: esto
rem le dice a PowerShell que corra este, y solo este, sin cambiar nada del
rem sistema (-ExecutionPolicy Bypass vale para esta vez y nada mas).

cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0publicar.ps1" %*
pause
