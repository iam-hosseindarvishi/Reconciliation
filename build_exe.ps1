Param(
    [switch]$OneFile
)

$py = "python"

Write-Host "Updating pip and installing required packaging tools..."
& $py -m pip install --upgrade pip
& $py -m pip install pyinstaller ttkbootstrap

if (Test-Path "requirements_pdf_persian.txt") {
    Write-Host "Installing PDF-related requirements from requirements_pdf_persian.txt..."
    & $py -m pip install -r requirements_pdf_persian.txt
}

$entry = "main.py"
$distName = "ReconciliationApp"

# Common folders to include as data (adjust as needed)
$folders = @("assets","config","database","ui","utils","Data")
$addData = @()
foreach ($f in $folders) {
    if (Test-Path $f) {
        # PyInstaller on Windows expects src;dest with semicolon
        $addData += "$f;$f"
    }
}

# Convert to CLI args (PowerShell 5.1 compatible)
$addDataArgsList = @()
foreach ($d in $addData) {
    $addDataArgsList += "--add-data `"$d`""
}
$addDataArgs = $addDataArgsList -join " "

$oneFileFlag = if ($OneFile) { "--onefile" } else { "--onedir" }

$cmd = "pyinstaller --noconfirm --clean $oneFileFlag --name $distName $addDataArgs --log-level=INFO $entry"

Write-Host "Running PyInstaller command:"
Write-Host $cmd

Invoke-Expression $cmd

Write-Host "Build finished. Check the dist\$distName folder for the output (or dist\$distName.exe if --onefile was used)."
Write-Host "If the exe is missing runtime libraries or fonts, ensure required packages are installed and add any missing data files via --add-data."
