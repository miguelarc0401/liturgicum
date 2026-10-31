@echo off
rem editar.bat - la app en este ordenador, con permiso para corregirla.
rem
rem Doble clic aqui, o "editar" en la terminal desde esta carpeta. Abre la
rem app en el navegador, servida por Enchiridion\src\editar.py, y en ella:
rem   * se corrige cualquier texto: se selecciona, se pulsa "Corregir" y se
rem     escribe como debe quedar. Queda en data\fe_de_erratas.json, y cada
rem     fase lo vuelve a poner al rehacer los datos (src\erratas.py);
rem   * se quitan y se agregan oraciones del devocionario.
rem Lo corregido lo ven todos cuando se publica.
rem
rem Es un .bat y no un .ps1 porque Windows no deja correr los .ps1 mientras
rem no se cambie la politica de ejecucion, y esto no ha de pedir nada.
rem Para pararlo, se cierra esta ventana (o Ctrl+C).

cd /d "%~dp0"
python Enchiridion\src\editar.py %*
if errorlevel 1 pause
