# Inicia a API e o Metro do VisualMatch no Windows; equivalente ao run-macos.sh.
# Execute pelo run-windows.bat, que libera a ExecutionPolicy apenas para esta execução.
# Compatível com o Windows PowerShell 5.1.

$ErrorActionPreference = 'Stop'

$RootDir = $PSScriptRoot
$ApiDir = Join-Path $RootDir 'VisualMatch.API'
$AppDir = Join-Path $RootDir 'VisualMatch.APP'
$ApiPort = if ($env:VISUALMATCH_API_PORT) { [int]$env:VISUALMATCH_API_PORT } else { 8000 }
$MetroPort = if ($env:VISUALMATCH_METRO_PORT) { [int]$env:VISUALMATCH_METRO_PORT } else { 8081 }
$EnvFile = Join-Path $AppDir '.env.local'
$ApiPython = Join-Path $ApiDir '.venv\Scripts\python.exe'
$ExportVenv = Join-Path $ApiDir '.venv-export'
$ExportPython = Join-Path $ExportVenv 'Scripts\python.exe'
$ExpoCli = Join-Path $AppDir 'node_modules\expo\bin\cli'

function Fail([string]$Message) {
    Write-Host "Erro: $Message" -ForegroundColor Red
    exit 2  # run-windows.bat keeps the window open on this code
}

function Test-PortInUse([int]$Port) {
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Get-LanIPv4 {
    # Adapter that holds the default route, like `route get default` on macOS.
    $config = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } | Select-Object -First 1
    if ($config) { return ($config.IPv4Address | Select-Object -First 1).IPAddress }
    $fallback = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
        Select-Object -First 1
    if ($fallback) { return $fallback.IPAddress }
    return $null
}

function Set-DotEnvValue([string]$Path, [string]$Key, [string]$Value) {
    # Keeps the other lines, replaces (or appends) KEY=value and drops duplicates.
    $lines = @()
    if (Test-Path -LiteralPath $Path) { $lines = @(Get-Content -LiteralPath $Path) }
    $updated = $false
    $result = @(foreach ($line in $lines) {
        if ($line -like "$Key=*") {
            if (-not $updated) { "$Key=$Value"; $updated = $true }
        } else {
            $line
        }
    })
    if (-not $updated) { $result += "$Key=$Value" }
    # UTF-8 without BOM: a BOM would hide the first key from Expo.
    [System.IO.File]::WriteAllLines($Path, [string[]]$result, (New-Object System.Text.UTF8Encoding $false))
}

function Get-MissingModels {
    # Asks the API's own registry; only ASCII ids cross stdout, never paths.
    Push-Location $ApiDir
    try {
        $output = & $ApiPython -c "from app import config; print(' '.join(spec.id for spec in config.MODELS.values() if not spec.path.exists()))"
    } finally {
        Pop-Location
    }
    if ($LASTEXITCODE -ne 0) { Fail 'não foi possível ler o registro de modelos da API.' }
    return "$output".Trim()
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Fail 'Node.js não encontrado. Instale o Node.js 20.19.4 ou superior.' }
$nodeVersion = "$(& node -p 'process.versions.node')".Trim()
if ([version]$nodeVersion -lt [version]'20.19.4') { Fail "Node.js $nodeVersion não é suportado. Instale a versão 20.19.4 ou superior." }
if (-not (Test-Path -LiteralPath $ApiPython)) { Fail 'Ambiente Python ausente. Crie-o em VisualMatch.API\.venv e instale requirements.txt.' }
if (-not (Test-Path -LiteralPath $ExpoCli)) { Fail 'Dependências do app ausentes. Execute npm install em VisualMatch.APP.' }

if (Test-PortInUse $ApiPort) { Fail "a porta $ApiPort já está em uso. Encerre o processo atual ou defina VISUALMATCH_API_PORT." }
if (Test-PortInUse $MetroPort) { Fail "a porta $MetroPort já está sendo usada, provavelmente por outro Metro. Encerre-o antes de continuar." }

# The ONNX files are not in git: export every registered model that is missing.
$missingModels = Get-MissingModels
if ($missingModels) {
    Write-Host "Modelos ausentes em VisualMatch.API\models ($missingModels); exportando a partir dos pesos oficiais."
    if (-not (Test-Path -LiteralPath $ExportPython)) {
        Write-Host "Primeira exportação: instalando PyTorch em $ExportVenv (alguns minutos)."
        & $ApiPython -m venv $ExportVenv
        & $ExportPython -m pip install -q -r (Join-Path $ApiDir 'requirements-export.txt')
        if ($LASTEXITCODE -ne 0) {
            Remove-Item -LiteralPath $ExportVenv -Recurse -Force
            Fail 'não foi possível instalar requirements-export.txt.'
        }
    }
    Push-Location $ApiDir
    try { & $ExportPython scripts\export_models.py } finally { Pop-Location }
    if ($LASTEXITCODE -ne 0) { Fail "não foi possível exportar os modelos: $missingModels." }
}

$lanIp = Get-LanIPv4
if (-not $lanIp) { Fail 'não foi possível descobrir o IP local do computador. Verifique a conexão de rede.' }
# No proxy as on macOS: the API listens on the network itself, which the Windows firewall allows per rule.
$apiUrl = "http://${lanIp}:$ApiPort"
$env:EXPO_PUBLIC_API_BASE_URL = $apiUrl
Set-DotEnvValue $EnvFile 'EXPO_PUBLIC_API_BASE_URL' $apiUrl

Write-Host 'VisualMatch'
Write-Host "  API local:       http://127.0.0.1:$ApiPort"
Write-Host "  API no celular:  $apiUrl"
Write-Host "  Model info:      $apiUrl/api/model-info"
Write-Host '  Modelos:         todos prontos na API; escolha qual usar no app'
Write-Host '  .env.local:      atualizado'
$firewallRule = $null
try { $firewallRule = Get-NetFirewallRule -DisplayName 'VisualMatch API' -ErrorAction SilentlyContinue } catch { }
if (-not $firewallRule) {
    Write-Host ''
    Write-Host 'Se o celular não acessar a API, libere a porta no firewall (PowerShell como administrador):' -ForegroundColor Yellow
    Write-Host "  New-NetFirewallRule -DisplayName 'VisualMatch API' -Direction Inbound -Action Allow -Protocol TCP -LocalPort $ApiPort" -ForegroundColor Yellow
}
Write-Host ''
Write-Host 'Use Ctrl+C para encerrar API e Metro.'
Write-Host ''

$api = $null
try {
    $api = Start-Process -FilePath $ApiPython -WorkingDirectory $ApiDir -NoNewWindow -PassThru `
        -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--reload', '--host', '0.0.0.0', '--port', "$ApiPort")
    Start-Sleep -Seconds 1
    if ($api.HasExited) { Fail 'a API encerrou durante a inicialização.' }

    Push-Location $AppDir
    try {
        # node + the Expo CLI directly: npm.cmd would ask "Terminate batch job (Y/N)?" on Ctrl+C.
        & node $ExpoCli start --dev-client --clear --port $MetroPort
    } finally {
        Pop-Location
    }
} finally {
    Write-Host ''
    Write-Host 'Encerrando VisualMatch...'
    if ($api -and -not $api.HasExited) {
        # /T also stops the uvicorn reloader's worker process.
        try { & taskkill.exe /PID $api.Id /T /F 2>&1 | Out-Null } catch { }  # already gone: nothing to stop
    }
}
