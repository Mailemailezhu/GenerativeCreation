# Build GC with PyInstaller (onedir), create shortcut, zip the release.
# Keep this file ASCII-only: Windows PowerShell 5.1 reads .ps1 as ANSI, and a UTF-8
# file without BOM turns Chinese comments into parser errors.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Py = Join-Path $Root "app\venv\Scripts\python.exe"
$Icon = Join-Path $Root "app\assets\gc.ico"
$Version = "0.1.0"

# 数组字面量里 "," 的优先级高于 "+"，拼接必须先算成变量，否则会被拆成两个参数
$Data = (Join-Path $Root "app\assets") + ":assets"

$PyArgs = @(
    "-m", "PyInstaller",
    "--noconfirm", "--clean", "--windowed", "--onedir",
    "--name", "GC",
    "--icon", $Icon,
    "--add-data", $Data,
    "--distpath", (Join-Path $Root "dist"),
    "--workpath", (Join-Path $Root "build\pyi"),
    "--specpath", (Join-Path $Root "build"),
    "--exclude-module", "tkinter",
    "--exclude-module", "matplotlib",
    "--exclude-module", "scipy",
    "--exclude-module", "pandas",
    "--exclude-module", "PyQt5.QtWebEngineWidgets",
    (Join-Path $Root "app\main.py")
)

Write-Host "[1/3] pyinstaller"
& $Py @PyArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed: $LASTEXITCODE" }

Write-Host "[2/3] shortcut"
$Exe = Join-Path $Root "dist\GC\GC.exe"
if (-not (Test-Path $Exe)) { throw "missing $Exe" }
$Shell = New-Object -ComObject WScript.Shell
$Lnk = $Shell.CreateShortcut((Join-Path $Root "GC.lnk"))
$Lnk.TargetPath = $Exe
$Lnk.WorkingDirectory = $Root
$Lnk.IconLocation = $Icon
$Lnk.Description = "GC generative workspace"
$Lnk.Save()

Write-Host "[3/3] zip"
$Rel = Join-Path $Root "release"
if (Test-Path $Rel) { Remove-Item $Rel -Recurse -Force }
New-Item -ItemType Directory -Path $Rel | Out-Null
Copy-Item (Join-Path $Root "dist\GC") -Destination $Rel -Recurse
Copy-Item (Join-Path $Root "workflows") -Destination $Rel -Recurse
Copy-Item (Join-Path $Root "README.md") -Destination $Rel
# launcher so users do not have to dig into the GC subfolder
$Bat = @(
    '@echo off',
    'start "" "%~dp0GC\GC.exe"'
)
Set-Content -Path (Join-Path $Rel "GC.bat") -Value $Bat -Encoding ASCII
New-Item -ItemType Directory -Path (Join-Path $Rel "config") | Out-Null
Copy-Item (Join-Path $Root "config\extra_model_paths.yaml") -Destination (Join-Path $Rel "config")
Copy-Item (Join-Path $Root "config\api_models.example.json") -Destination (Join-Path $Rel "config")
$Zip = Join-Path $Root ("release\GC-" + $Version + "-windows-x64.zip")
Compress-Archive -Path (Join-Path $Rel "*") -DestinationPath $Zip -CompressionLevel Optimal
Write-Host ("BUILD_OK " + $Exe)
Write-Host ("ZIP_OK " + $Zip + " " + [math]::Round((Get-Item $Zip).Length / 1MB, 1) + " MB")
