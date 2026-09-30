# Publicar.ps1 - de la carpeta del escritorio al telefono, en una orden.
#
#   1. rehace el calendario con el santoral y la precedencia (18_santoral.py)
#   2. rehace los datos de la app                            (15_app_data.py)
#   3. los sube a GitHub, que republica GitHub Pages
#   4. el telefono se entera solo: la app pregunta si hay version nueva al
#      abrirse y al volver a primer plano, y se recarga cuando la hay
#
# Uso:   .\publicar.ps1
#        .\publicar.ps1 -Mensaje "corrijo el grado de santa Cecilia"
#        .\publicar.ps1 -SoloConstruir      (rehace los datos y no sube nada)

param(
    [string]$Mensaje = "",
    [switch]$SoloConstruir
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Paso($texto) { Write-Host "`n== $texto" -ForegroundColor Cyan }

Paso "Calendario, santoral y precedencia"
python src/18_santoral.py
if ($LASTEXITCODE -ne 0) { throw "18_santoral.py fallo" }

Paso "Datos de la app"
python src/15_app_data.py
if ($LASTEXITCODE -ne 0) { throw "15_app_data.py fallo" }

if ($SoloConstruir) {
    Write-Host "`nHecho. No se ha subido nada (-SoloConstruir)." -ForegroundColor Green
    exit 0
}

Paso "Subiendo a GitHub"
if (-not (Test-Path ".git")) {
    throw "Esta carpeta todavia no es un repositorio git. Mira README.md, seccion 'La primera vez'."
}

git add -A
$hayCambios = git status --porcelain
if (-not $hayCambios) {
    Write-Host "`nNo hay nada que subir: los datos no han cambiado." -ForegroundColor Yellow
    exit 0
}

if (-not $Mensaje) {
    $Mensaje = "Actualizo el leccionario ({0})" -f (Get-Date -Format "yyyy-MM-dd HH:mm")
}
git commit -m $Mensaje
if ($LASTEXITCODE -ne 0) { throw "git commit fallo" }

git push
if ($LASTEXITCODE -ne 0) { throw "git push fallo" }

Write-Host "`nSubido. GitHub Pages tarda un par de minutos en republicar." -ForegroundColor Green
Write-Host "Puedes seguirlo en la pestana Actions del repositorio."
