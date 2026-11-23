$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python scripts/build_filtered_xml.py
git add config docs
$changes = git status --porcelain
if (-not $changes) {
    Write-Host "Gönderilecek değişiklik yok."
    exit 0
}
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "XML ürün listesini güncelle: $stamp"
git push
Write-Host "Değişiklikler GitHub'a gönderildi."
