# Kopya Dosya Bulucu 🔍

Bir klasörde (alt klasörler dahil) içeriği birebir aynı olan dosyaları bulan ve kaç MB yer kazanabileceğinizi gösteren küçük bir Python aracı.

```
[1] 3 kopya × 24,6 MB
    asıl   Videolar/dogum-gunu.mp4
    kopya  İndirilenler/dogum-gunu.mp4
    kopya  İndirilenler/dogum-gunu (1).mp4
[2] 2 kopya × 1,2 MB
    asıl   rapor.pdf
    kopya  Eski/rapor-son.pdf

2 grupta 3 fazla kopya var. Silinirse 50,4 MB yer açılır.
```

## Özellikler

- Dosya adına değil **içeriğe** bakar (SHA-256), adı farklı kopyaları da bulur.
- Hızlıdır: önce boyuta, sonra ilk 64 KB'a, en son tüm içeriğe bakar.
- En eski dosyayı **asıl** kabul eder.
- `--tasi` ile fazla kopyaları silmek yerine ayrı bir klasöre taşır; klasör yapısı korunur, hiçbir dosya silinmez.
- Gizli dosya ve klasörleri (`.git` gibi) ve kısayolları atlar.
- `--json` ile başka araçlarda kullanılabilecek çıktı verir.
- Ek kütüphane gerektirmez; yalnızca Python 3.9+.

## Kullanım

```bash
python kopya_bulucu.py İndirilenler
python kopya_bulucu.py "C:\Users\ben\Resimler" --min-boyut 500KB
python kopya_bulucu.py İndirilenler --tasi Kopyalar
python kopya_bulucu.py İndirilenler --json > rapor.json
```

## Testler

```bash
python -m unittest -v
```
