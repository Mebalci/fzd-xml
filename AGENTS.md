# FZD XML Filter — Codex çalışma talimatları

Bu proje Kadıoğlu kaynak XML'ini indirir, yalnızca `config/products.json` içindeki aktif ürünleri seçer, ek görselleri XML'e ekler ve sonucu GitHub Pages üzerinde yayımlar.

## Değiştirilebilecek alanlar

- Ürün listesi ve ek görseller: `config/products.json`
- Kaynak adresi ve çalışma kuralları: `config/settings.json`
- XML filtreleme mantığı: `scripts/xml_core.py`
- Otomatik üretim: `scripts/build_filtered_xml.py`
- Yerel panel: `scripts/admin_server.py` ve `admin/`
- GitHub otomasyonu: `.github/workflows/publish-xml.yml`

## Zorunlu güvenlik kuralları

- Hiç ürün eşleşmezse boş XML yayımlama.
- Bir ürün bulunamazsa varsayılan olarak mevcut çıktıyı değiştirme.
- Eşleştirmede barkod, üretici kodu, ürün kodu ve kaynak ID alanlarını kullan.
- Kaynak ürün düğümündeki fiyat, stok, kategori ve diğer alanları değiştirme.
- Ek görselleri `RESIM2` alanından başlayarak ekle; kaynak `RESIM1` alanını koru.
- `config/products.json` içinde parola, GitHub tokenı veya başka bir gizli bilgi tutma.
- GitHub Actions izinlerini yalnızca gereken seviyede tut.

## Her değişiklikten sonra

```bash
python -m unittest discover -s tests -v
python scripts/build_filtered_xml.py --source-file tests/fixture.xml --output docs/test-urunler.xml
```

Test çıktısında tam 6 ürün bulunmalı ve `ISTENMEYEN` kodlu ürün yer almamalı. Gerçek kaynakla test yalnızca ağ erişimi varsa yapılmalıdır.

## Yeni ürün ekleme

Tercihen yerel paneli aç:

```bash
python scripts/admin_server.py
```

Sonra `http://127.0.0.1:8765` adresinde kaynak XML'de ara ve ürünü listeye ekle. Elle düzenlenecekse ürün kaydında en az bir eşleştirme alanı bulunmalı; barkod tercih edilir.
