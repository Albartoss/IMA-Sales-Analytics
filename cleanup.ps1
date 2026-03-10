# IMA-Sales-Analytics - Proje Temizleme Scripti
# Proje klasöründe çalıştır:
# PowerShell'de: .\cleanup.ps1

$root = Get-Location

# ── 1. SİLİNECEK DOSYALAR ────────────────────────────────────────────────────
$filesToDelete = @(
    "proje_yapisi.txt",
    "README.txt",
    "1.iss",
    "products_20250519_134404.csv",
    "products_20250519_134404.xlsx",
    "sales_20250519_134404.csv",
    "sales_20250519_134404.xlsx",
    "stock_transactions_20250519_134404.csv",
    "stock_transactions_20250519_134404.xlsx",
    "modules\forecast_plot.html"
)

foreach ($f in $filesToDelete) {
    $path = Join-Path $root $f
    if (Test-Path $path) {
        Remove-Item $path -Force
        Write-Host "Silindi: $f" -ForegroundColor Yellow
    }
}

# Diploma PDF - isim Kiril harfli olduğundan wildcard ile siliyoruz
Get-ChildItem -Path $root -Filter "*.pdf" | Remove-Item -Force
Write-Host "Silindi: *.pdf dosyaları" -ForegroundColor Yellow

# ── 2. KLASÖR TAŞIMA ─────────────────────────────────────────────────────────
# 1.iss -> installer/ klasörüne (eğer hala varsa)
$issFile = Join-Path $root "1.iss"
if (Test-Path $issFile) {
    New-Item -ItemType Directory -Force -Path (Join-Path $root "installer") | Out-Null
    Move-Item $issFile (Join-Path $root "installer\setup.iss") -Force
    Write-Host "Taşındı: 1.iss -> installer/setup.iss" -ForegroundColor Cyan
}

# sample_data klasörü boşsa bir placeholder ekle
$sampleDir = Join-Path $root "sample_data"
if ((Get-ChildItem $sampleDir | Measure-Object).Count -eq 0) {
    "Bu klasör örnek CSV dosyaları içindir. generate_synthetic_data.py çalıştırarak data/ klasörüne veri üretebilirsiniz." | 
    Out-File (Join-Path $sampleDir "README.txt") -Encoding UTF8
    Write-Host "Eklendi: sample_data/README.txt" -ForegroundColor Cyan
}

# ── 3. .gitignore OLUŞTUR ────────────────────────────────────────────────────
$gitignore = @"
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
*.egg-info/
dist/
build/

# Virtual environment
venv/
env/
.venv/

# IDE
.vs/
.vscode/
.idea/
*.suo
*.user

# Database (runtime'da üretiliyor)
database/inventory.db
database/*.db

# Data klasörü (generate_synthetic_data.py ile üretiliyor)
data/

# Runtime çıktıları
modules/forecast_plot.html
*.html

# Export dosyaları
*_export_*.csv
*_export_*.xlsx
products_*.csv
products_*.xlsx
sales_*.csv
sales_*.xlsx
stock_transactions_*.csv
stock_transactions_*.xlsx

# OS
.DS_Store
Thumbs.db
desktop.ini

# Kişisel belgeler
*.pdf
proje_yapisi.txt

# PyInstaller
*.spec
# main.spec'i takip etmek istersen üstteki satırı silin
"@

$gitignorePath = Join-Path $root ".gitignore"
$gitignore | Out-File $gitignorePath -Encoding UTF8
Write-Host "Oluşturuldu: .gitignore" -ForegroundColor Green

# ── 4. ÖZET ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== TEMIZLIK TAMAMLANDI ===" -ForegroundColor Green
Write-Host "Sonraki adımlar:" -ForegroundColor White
Write-Host "  1. git add -A" -ForegroundColor White
Write-Host "  2. git commit -m 'chore: clean up project structure, add .gitignore'" -ForegroundColor White
Write-Host "  3. git push" -ForegroundColor White
