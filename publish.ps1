$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python scripts/build_filtered_xml.py
if ($LASTEXITCODE -ne 0) {
    throw "XML oluşturulamadı. GitHub'a hiçbir değişiklik gönderilmedi."
}

git add config docs
$changes = git diff --cached --name-only
if (-not $changes) {
    Write-Host "Gönderilecek değişiklik yok."
    exit 0
}

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "XML ürün listesini güncelle: $stamp"
if ($LASTEXITCODE -ne 0) {
    throw "Git commit oluşturulamadı."
}

git push
if ($LASTEXITCODE -ne 0) {
    throw "GitHub'a gönderme başarısız oldu."
}

Write-Host "Değişiklikler GitHub'a gönderildi."
