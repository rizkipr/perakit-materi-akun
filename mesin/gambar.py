"""Primitif gambar untuk perakit materi listing akun.

Modul ini tidak tahu apa pun tentang template atau struktur folder — hanya
operasi gambar murni, supaya bisa diuji tanpa aset apa pun.
"""
from __future__ import annotations

from typing import Optional

from PIL import Image, ImageDraw, ImageFont

# Sisakan napas di tepi kotak. Teks yang menyentuh garis isian terbaca sesak,
# dan isian pada template punya tepi bercahaya yang ikut termakan.
JEDA = 0.86


def skala_menutup(im: Image.Image, lebar: int, tinggi: int) -> Image.Image:
    """Skalakan `im` sampai MENUTUP kotak lebar×tinggi, lalu potong kelebihannya.

    Menutup, bukan memuat ke dalam. Slot pada template transparan, jadi gambar
    yang cuma "dimuat" akan menyisakan tepi tembus yang menganga — cacat yang
    baru terlihat setelah 30 kartu jadi.
    """
    if lebar <= 0 or tinggi <= 0:
        raise ValueError(f'ukuran slot tidak masuk akal: {lebar}x{tinggi}')

    im = im.convert('RGBA')
    faktor = max(lebar / im.width, tinggi / im.height)
    ukuran = (max(lebar, round(im.width * faktor)), max(tinggi, round(im.height * faktor)))
    im = im.resize(ukuran, Image.Resampling.LANCZOS)

    kiri = (im.width - lebar) // 2
    atas = (im.height - tinggi) // 2
    return im.crop((kiri, atas, kiri + lebar, atas + tinggi))


def muat_font(berkas: str, ukuran: int, variasi: Optional[str] = None):
    """Muat font, dan pilih bobotnya kalau ini font variabel.

    Orbitron di google/fonts hanya ada sebagai `Orbitron[wght].ttf` — tidak ada
    berkas Bold statis. Tanpa langkah ini semua angka tercetak Regular, dan
    bedanya cukup halus untuk lolos sampai 30 kartu jadi.
    """
    font = ImageFont.truetype(berkas, ukuran)
    if variasi:
        font.set_variation_by_name(variasi)
    return font


def teks_di_kotak(kanvas: Image.Image, kotak, teks: str, berkas_font: str,
                  warna, ukuran_awal: int, ukuran_min: int = 16,
                  variasi: Optional[str] = None) -> int:
    """Tulis `teks` rata tengah di dalam `kotak` = (x, y, lebar, tinggi).

    Ukuran font mengecil sampai muat. Harga bisa 750.000 atau 12.500.000, dan
    isian pada template lebarnya tetap — tanpa penyusutan, angka panjang akan
    meluber menimpa ornamen di sebelahnya.

    Mengembalikan ukuran font yang akhirnya dipakai.
    """
    x, y, lebar, tinggi = kotak
    pena = ImageDraw.Draw(kanvas)

    ukuran = ukuran_awal
    while True:
        font = muat_font(berkas_font, ukuran, variasi)
        kiri, atas, kanan, bawah = pena.textbbox((0, 0), teks, font=font)
        lebar_teks, tinggi_teks = kanan - kiri, bawah - atas
        muat = lebar_teks <= lebar * JEDA and tinggi_teks <= tinggi * JEDA
        if muat or ukuran <= ukuran_min:
            break
        ukuran -= 2

    pena.text((x + (lebar - lebar_teks) / 2 - kiri,
               y + (tinggi - tinggi_teks) / 2 - atas),
              teks, font=font, fill=warna)
    return ukuran
