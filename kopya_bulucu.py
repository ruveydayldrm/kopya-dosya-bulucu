#!/usr/bin/env python3
"""Kopya Dosya Bulucu — bir klasörde içeriği birebir aynı olan dosyaları bulur.

Kullanım:
    python kopya_bulucu.py İndirilenler
    python kopya_bulucu.py İndirilenler --min-boyut 1MB
    python kopya_bulucu.py İndirilenler --tasi Kopyalar     # Fazlalıkları bir klasöre taşı
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ON_OKUMA = 64 * 1024  # Önce yalnızca ilk 64 KB karşılaştırılır
PARCA = 1024 * 1024
BIRIMLER = {"": 1, "B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}


# --- Tarama ------------------------------------------------------------------

def boyuta_gore_grupla(kok: Path, min_boyut: int = 1, haric: Path | None = None) -> dict[int, list[Path]]:
    """Gizli klasörleri ve kısayolları atlayarak dosyaları boyutlarına göre gruplar."""
    gruplar: dict[int, list[Path]] = defaultdict(list)
    haric = haric.resolve() if haric else None
    for klasor, alt_klasorler, dosyalar in os.walk(kok):
        alt_klasorler[:] = [
            a for a in alt_klasorler
            if not a.startswith(".") and (haric is None or (Path(klasor) / a).resolve() != haric)
        ]
        for ad in dosyalar:
            if ad.startswith("."):
                continue
            yol = Path(klasor) / ad
            try:
                if yol.is_symlink() or not yol.is_file():
                    continue
                boyut = yol.stat().st_size
            except OSError:
                continue
            if boyut >= min_boyut:
                gruplar[boyut].append(yol)
    return gruplar


def ozet_al(yol: Path, sinir: int | None = None) -> str:
    """Dosyanın SHA-256 özetini döner; sinir verilirse yalnızca ilk sinir bayt okunur."""
    h = hashlib.sha256()
    kalan = sinir
    with open(yol, "rb") as f:
        while kalan is None or kalan > 0:
            parca = f.read(PARCA if kalan is None else min(PARCA, kalan))
            if not parca:
                break
            h.update(parca)
            if kalan is not None:
                kalan -= len(parca)
    return h.hexdigest()


def _ozete_gore_ayir(yollar: list[Path], sinir: int | None) -> list[list[Path]]:
    gruplar: dict[str, list[Path]] = defaultdict(list)
    for yol in yollar:
        try:
            gruplar[ozet_al(yol, sinir)].append(yol)
        except OSError:
            continue  # Okunamayan dosyaları atla
    return [g for g in gruplar.values() if len(g) > 1]


def kopyalari_bul(kok: Path, min_boyut: int = 1, haric: Path | None = None) -> list[list[Path]]:
    """Aynı içerikli dosya gruplarını döner. Hız için üç aşamalıdır:
    boyut → ilk 64 KB'ın özeti → tüm dosyanın özeti.
    Her grubun ilk elemanı en eski dosyadır (asıl kabul edilir)."""
    sonuc = []
    for boyut, yollar in boyuta_gore_grupla(kok, min_boyut, haric).items():
        if len(yollar) < 2:
            continue
        for aday in _ozete_gore_ayir(yollar, ON_OKUMA):
            kesin = [aday] if boyut <= ON_OKUMA else _ozete_gore_ayir(aday, None)
            sonuc.extend(kesin)
    for grup in sonuc:
        grup.sort(key=lambda p: (p.stat().st_mtime, len(str(p)), str(p)))
    sonuc.sort(key=lambda g: (-bosa_giden([g]), str(g[0])))
    return sonuc


def bosa_giden(gruplar: list[list[Path]]) -> int:
    """Her gruptan yalnızca bir kopya tutulsa kazanılacak bayt."""
    return sum(g[0].stat().st_size * (len(g) - 1) for g in gruplar)


# --- Taşıma ------------------------------------------------------------------

def bos_ad(yol: Path) -> Path:
    sayi = 1
    aday = yol
    while aday.exists():
        aday = yol.with_name(f"{yol.stem} ({sayi}){yol.suffix}")
        sayi += 1
    return aday


def fazlaliklari_tasi(gruplar: list[list[Path]], kok: Path, hedef: Path) -> list[tuple[Path, Path]]:
    """Her gruptaki asıl dosyayı yerinde bırakır, diğerlerini hedefe klasör yapısını koruyarak taşır."""
    tasinan = []
    for grup in gruplar:
        for yol in grup[1:]:
            yeni = bos_ad(hedef / yol.relative_to(kok))
            yeni.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(yol), str(yeni))
            tasinan.append((yol, yeni))
    return tasinan


# --- Biçimlendirme -----------------------------------------------------------

def boyut_yaz(bayt: int) -> str:
    for birim, carpan in (("GB", 1024 ** 3), ("MB", 1024 ** 2), ("KB", 1024)):
        if bayt >= carpan:
            return f"{bayt / carpan:.1f} {birim}".replace(".", ",")
    return f"{bayt} B"


def boyut_coz(metin: str) -> int:
    """'500', '200KB', '1,5 MB' → bayt"""
    m = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*([KMG]?B?)\s*", metin.upper())
    if not m or m.group(2) not in BIRIMLER:
        raise argparse.ArgumentTypeError(f"Geçersiz boyut: {metin} (örn: 500KB, 2MB)")
    return int(float(m.group(1).replace(",", ".")) * BIRIMLER[m.group(2)])


# --- Komut satırı ------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="kopya_bulucu", description="İçeriği aynı olan dosyaları bulur.")
    p.add_argument("klasor", nargs="?", default=".", help="Taranacak klasör (alt klasörler dahil)")
    p.add_argument("--min-boyut", type=boyut_coz, default=1, help="Bundan küçük dosyaları atla, örn: 100KB")
    p.add_argument("--tasi", metavar="KLASOR", help="Fazla kopyaları bu klasöre taşı (en eski dosya yerinde kalır)")
    p.add_argument("--json", action="store_true", help="Sonucu JSON olarak yaz")
    args = p.parse_args(argv)

    kok = Path(args.klasor).expanduser()
    if not kok.is_dir():
        print(f"Klasör bulunamadı: {kok}", file=sys.stderr)
        return 1
    hedef = Path(args.tasi).expanduser() if args.tasi else None

    gruplar = kopyalari_bul(kok, max(1, args.min_boyut), hedef)
    kazanc = bosa_giden(gruplar)

    if args.json:
        print(json.dumps({
            "gruplar": [{"boyut": g[0].stat().st_size, "dosyalar": [str(y) for y in g]} for g in gruplar],
            "kazanilacak_bayt": kazanc,
        }, ensure_ascii=False, indent=2))
    elif not gruplar:
        print("Kopya dosya bulunamadı. 🎉")
        return 0
    else:
        for i, grup in enumerate(gruplar, 1):
            print(f"[{i}] {len(grup)} kopya × {boyut_yaz(grup[0].stat().st_size)}")
            for j, yol in enumerate(grup):
                print(f"    {'asıl ' if j == 0 else 'kopya'}  {yol.relative_to(kok)}")
        fazla = sum(len(g) - 1 for g in gruplar)
        print(f"\n{len(gruplar)} grupta {fazla} fazla kopya var. Silinirse {boyut_yaz(kazanc)} yer açılır.")

    if hedef and gruplar:
        tasinan = fazlaliklari_tasi(gruplar, kok, hedef)
        if not args.json:
            print(f"{len(tasinan)} kopya {hedef} klasörüne taşındı. Kontrol edip silebilirsiniz.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
