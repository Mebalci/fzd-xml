# FZD seçili ürün XML servisi

Bu proje Kadıoğlu XML kaynağından yalnızca seçilen ürünleri çıkarır ve Qukasoft'un okuyabileceği yeni bir XML adresi oluşturur. GitHub Actions işlemi 6 saatte bir çalıştırır; GitHub Pages XML'i sürekli erişilebilir tutar.

## Hazır gelen ürünler

- 3200.31566
- 3200.31049
- 3200.31710
- 3200.31709
- 3200.31623
- 3200.30908

## Bilgisayarda çalıştırma

Python 3.10 veya üzeri yeterlidir. Ek paket kurulmaz.

Windows'ta `start-panel.bat` dosyasına çift tıkla. Panel açılmazsa tarayıcıda `http://127.0.0.1:8765` adresine git.

VS Code içinden `Terminal > Run Task` menüsünde şu görevler bulunur:

- `FZD: Yönetim panelini aç`
- `FZD: XML'i yerelde oluştur`
- `FZD: Testleri çalıştır`
- `FZD: GitHub'a gönder`

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

Bu adresi Qukasoft'ta yeni ve ayrı bir XML kaynağı olarak kullan.

## Qukasoft ayarı

- Eski Kadıoğlu XML kaynağının adresini değiştirme.
- Yeni bir XML kaynağı oluştur.
- Yeni kaynakta `urunler.xml` adresini kullan.
- İlk testte zamanlamayı `Hiçbir Zaman` bırak.
- Kaynak etiketlerini eşleştir ve yalnızca bir kez `Ürünleri Aktar` çalıştır.
- Sonuçta tam 6 ürün bulunduğunu işlem logundan doğrula.
- Doğruladıktan sonra 6 saatlik veya günlük zamanlamayı aç.

## Hata güvenliği

- Seçili ürünlerden biri kaynakta bulunamazsa işlem hata verir ve eksik XML yayımlanmaz.
- Hiç ürün eşleşmezse boş XML oluşturulmaz.
- Qukasoft bu nedenle geçici kaynak hatasında ürünleri yanlışlıkla silinmiş görmez.
- `docs/status.json` son başarılı üretimin özetini içerir.

## Önemli

GitHub Pages'teki yönetim sayfası salt okunur durum ekranıdır. Ürün ekleme ve silme işlemleri güvenlik nedeniyle bilgisayardaki yerel panelden yapılır. GitHub tokenını web sayfasına koyma.
