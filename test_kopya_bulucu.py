import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

import kopya_bulucu


class KopyaBulucuTesti(unittest.TestCase):
    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self.kok = Path(self._gecici.name)

    def tearDown(self):
        self._gecici.cleanup()

    def dosya(self, yol, icerik, zaman=None):
        tam = self.kok / yol
        tam.parent.mkdir(parents=True, exist_ok=True)
        tam.write_bytes(icerik)
        if zaman is not None:
            os.utime(tam, (zaman, zaman))
        return tam

    def test_ayni_icerik_bulunur_en_eski_asil_olur(self):
        yeni = self.dosya("a.txt", b"merhaba", zaman=2_000_000)
        eski = self.dosya("alt/b.txt", b"merhaba", zaman=1_000_000)
        self.dosya("c.txt", b"merhabb")  # aynı boyut, farklı içerik
        self.dosya("d.txt", b"bambaska")
        self.assertEqual(kopya_bulucu.kopyalari_bul(self.kok), [[eski, yeni]])

    def test_buyuk_dosyalar_sadece_basa_bakilarak_eslenmez(self):
        bas = b"x" * (kopya_bulucu.ON_OKUMA + 10)
        self.dosya("bir.bin", bas + b"1")
        self.dosya("iki.bin", bas + b"2")
        self.dosya("uc.bin", bas + b"1")
        gruplar = kopya_bulucu.kopyalari_bul(self.kok)
        self.assertEqual(len(gruplar), 1)
        self.assertEqual(sorted(p.name for p in gruplar[0]), ["bir.bin", "uc.bin"])

    def test_bosa_giden_alan(self):
        for ad in ["a", "b", "c"]:
            self.dosya(ad, b"1234567890")
        self.assertEqual(kopya_bulucu.bosa_giden(kopya_bulucu.kopyalari_bul(self.kok)), 20)

    def test_gizli_ve_kucuk_dosyalar_atlanir(self):
        self.dosya(".gizli", b"ayni")
        self.dosya(".git/x", b"ayni")
        self.dosya("gorunur", b"ayni")
        self.assertEqual(kopya_bulucu.kopyalari_bul(self.kok), [])

        self.dosya("k1", b"ab")
        self.dosya("k2", b"ab")
        self.assertEqual(kopya_bulucu.kopyalari_bul(self.kok, min_boyut=3), [])

    def test_fazlaliklar_tasinir(self):
        self.dosya("a.txt", b"ayni", zaman=1_000_000)
        self.dosya("klasor/a.txt", b"ayni", zaman=2_000_000)
        hedef = self.kok / "Kopyalar"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(kopya_bulucu.main([str(self.kok), "--tasi", str(hedef)]), 0)
        self.assertTrue((self.kok / "a.txt").exists())
        self.assertFalse((self.kok / "klasor/a.txt").exists())
        self.assertEqual((hedef / "klasor/a.txt").read_bytes(), b"ayni")
        # İkinci çalıştırmada taşınan klasör yeniden taranmaz
        self.assertEqual(kopya_bulucu.kopyalari_bul(self.kok, haric=hedef), [])

    def test_boyut_cevirileri(self):
        self.assertEqual(kopya_bulucu.boyut_coz("500"), 500)
        self.assertEqual(kopya_bulucu.boyut_coz("2kb"), 2048)
        self.assertEqual(kopya_bulucu.boyut_coz("1,5 MB"), 1572864)
        self.assertEqual(kopya_bulucu.boyut_yaz(1572864), "1,5 MB")
        self.assertEqual(kopya_bulucu.boyut_yaz(12), "12 B")


if __name__ == "__main__":
    unittest.main()
