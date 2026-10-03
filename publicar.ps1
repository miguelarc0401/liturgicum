# Publicar.ps1 - de la carpeta del escritorio al telefono, en una orden.
#
#   1. rehace el calendario con el santoral y la precedencia (18_santoral.py)
#   2. rehace la liturgia de las horas para la app  (Breviarium/src/4_app.py)
#   3. rehace los datos de la app                            (15_app_data.py)
#   4. los sube a GitHub, que republica GitHub Pages
#   5. el telefono se entera solo: la app pregunta si hay version nueva al
#      abrirse y al volver a primer plano, y se recarga cuando la hay
#
# El orden de 2 y 3 importa: 15_app_data.py firma TODO lo que hay en
# app/datos/, y esa firma es la que obliga al service worker del telefono a
# tirar su cache. Si las horas se rehicieran despues, la firma se quedaria
# vieja y el telefono seguiria rezando con los textos de antes.
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

Paso "Liturgia de las horas"
python Breviarium/src/4_app.py
if ($LASTEXITCODE -ne 0) { throw "Breviarium/src/4_app.py fallo" }

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

# Antes de commitear, mirar si entra algo gordo. `git add -A` lo coge todo, y
# una carpeta de fuentes nueva -los cien misalitos del Missale fueron 364 MB-
# se cuela sin que nadie lo note y se queda en la historia para siempre, que
# es de donde ya no se saca sin reescribirla. Esto no decide: avisa, con los
# ficheros por delante, y espera un "s".
$umbralMB = 5
$gordos = @()
foreach ($ruta in (git diff --cached --name-only --diff-filter=AM)) {
    if (Test-Path -LiteralPath $ruta -PathType Leaf) {
        $mb = (Get-Item -LiteralPath $ruta).Length / 1MB
        if ($mb -ge $umbralMB) { $gordos += [pscustomobject]@{ MB = $mb; Ruta = $ruta } }
    }
}
if ($gordos.Count -gt 0) {
    $totalMB = ($gordos | Measure-Object -Property MB -Sum).Sum
    Write-Host ""
    Write-Host ("Van a entrar {0} fichero(s) de mas de {1} MB, {2:N0} MB en total:" -f `
        $gordos.Count, $umbralMB, $totalMB) -ForegroundColor Yellow
    foreach ($g in ($gordos | Sort-Object -Property MB -Descending | Select-Object -First 12)) {
        Write-Host ("   {0,8:N1} MB  {1}" -f $g.MB, $g.Ruta)
    }
    if ($gordos.Count -gt 12) {
        Write-Host ("   ... y {0} mas" -f ($gordos.Count - 12))
    }
    Write-Host ""
    Write-Host "Si son fuentes -PDF, volcados, cosas que se vuelven a generar con una" -ForegroundColor Yellow
    Write-Host "orden-, no van al repositorio: ponlas en .gitignore y vuelve a intentarlo." -ForegroundColor Yellow
    $r = Read-Host "Subirlos de todos modos? (escribe si)"
    if ($r -notin @("si", "SI", "Si", "s", "S", "yes", "y")) {
        git reset --quiet
        Write-Host "`nNo se ha subido nada. Lo que habia preparado se ha des-preparado." -ForegroundColor Yellow
        exit 1
    }
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
