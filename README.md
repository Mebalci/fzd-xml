# FZD seçili ürün XML servisi

## Panel kullanımı

1. Kaynak XML'de ürün kodu, barkod, marka veya ürün adıyla ara.
2. `Listeye ekle` düğmesine bas.
3. Gerekirse her satıra bir ek görsel URL'si gir.
4. `Değişiklikleri kaydet` düğmesine bas.
5. `XML'i şimdi oluştur` ile gerçek kaynakta test et.
6. Sonuç doğruysa `publish.ps1` dosyasını çalıştır veya VS Code görevinden GitHub'a gönder.

### Excel ile toplu ürün düzenleme

1. Panelde `Excel'e aktar` düğmesine bas ve kayıtlı ürün listesini indir.
2. `Ürünler` sayfasında mevcut satırları düzenle veya yeni satırlar ekle.
3. Sütun başlıklarını değiştirme. Barkod, ürün kodu, üretici kodu ve kaynak ID hücreleri metin olarak biçimlendirilmiştir.
4. Dosyayı `.xlsx` biçiminde kaydet.
5. Panelde içe aktarma yöntemini seç: mevcut listeyi değiştir veya mevcut listeye ekle.
6. `Excel'den içe aktar` ile dosyayı seç. Hatalı ya da yinelenen eşleştirme alanı varsa liste değiştirilmez.
7. Önizlemeyi kontrol et ve `Değişiklikleri kaydet` düğmesine bas.
8. `XML'i şimdi oluştur` ile doğrula, ardından `publish.ps1` ile GitHub'a gönder.

## GitHub kurulumu

1. GitHub'da public bir repository oluştur. Örnek ad: `fzd-xml`.
2. Bu klasörü VS Code ile aç.
3. Terminalde aşağıdaki komutları çalıştır:

```bash
git init
git add .
git commit -m "FZD XML filtre servisini kur"
git branch -M main
git remote add origin https://github.com/KULLANICI_ADI/fzd-xml.git
git push -u origin main
```

4. GitHub repository içinde `Settings > Pages` bölümünü aç.
5. `Build and deployment > Source` alanında **GitHub Actions** seç.
6. `Actions` sekmesinde `XML'i güncelle ve yayınla` işleminin bitmesini bekle.

Yayın adresi genellikle şöyledir:

```text
https://KULLANICI_ADI.github.io/fzd-xml/urunler.xml
```
## Hata güvenliği

- Seçili ürünlerden biri kaynakta bulunamazsa işlem hata verir ve eksik XML yayımlanmaz.
- Hiç ürün eşleşmezse boş XML oluşturulmaz.
- Qukasoft bu nedenle geçici kaynak hatasında ürünleri yanlışlıkla silinmiş görmez.
- `docs/status.json` son başarılı üretimin özetini içerir.

## Önemli

GitHub Pages'teki yönetim sayfası salt okunur durum ekranıdır. Ürün ekleme ve silme işlemleri güvenlik nedeniyle bilgisayardaki yerel panelden yapılır. GitHub tokenını web sayfasına koyma.
