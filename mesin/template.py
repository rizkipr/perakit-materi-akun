"""Perakit kartu dari template Photoshop milik pemilik.

Koordinat di bawah dibaca langsung dari catatan lapisan Template_Jago_Topup.psd
(8 Agu 2026), bukan diukur dari gambar. Kalau template diubah di Photoshop,
koordinat ini harus dibaca ulang dari PSD-nya, bukan ditebak dari PNG-nya.

Seluruh jendela gambar pada template TRANSPARAN penuh. Jadi isi ditaruh di
belakang lalu template ditempel di atasnya — bingkainya sendiri yang memotong
bentuk tak beraturan di sudut-sudut api. Tidak perlu masking.

Kolom isian teks justru buram, jadi teks ditulis DI ATAS template.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image

import antrean
import gambar

KANVAS = (2613, 3264)
EKSPOR = (2608, 3260)            # tepat 4:5, sesuai aspect-ratio kartu di situs
EKSPOR_MUTU = 100                # mutu WEBP
# 95 dulu dipilih waktu kuota unggah belum diketahui. Setelah pemilik menyebut
# batasnya 5120 KB, 100 jadi murah: 1099 KB naik ke 1574 KB, masih 31% kuota.
# Ini satu-satunya tuas yang tersisa yang menambah detail SUNGGUHAN pada kartu
# — ia berhenti membuang informasi saat mengompres.
#
# Membesarkan ekspor melewati kanvas TIDAK ditempuh, walau kuotanya cukup:
# artwork template lahir 2613x3264 (diperiksa pada template-master.psd, yang
# ternyata juga 2613x3264), jadi ukuran di atas itu cuma memperbesar piksel
# yang sama. Poster rujukan pemilik yang 4100x5120 pun ternyata kartu 2613
# yang diperbesar 1,569x, bukan desain beresolusi lebih tinggi.
# Batas unggah situs jagotopup, disebutkan pemilik 9 Agu. Ditulis di sini
# supaya mesin bisa menolak kartu yang tidak akan bisa diunggah — pemilik
# tidak boleh baru tahu saat mengunggah tiga puluh berkas satu per satu.
BATAS_UNGGAH_KB = 5120
# 1080x1350 dulu cukup, sampai karakter mulai dinaikkan 4x oleh upscaler.
# Diukur 9 Agu: kutout keluar 2280px, digambar di poster 1724px, lalu
# dikecilkan lagi jadi 713px di ekspor — tiga per empat kerja upscaler dibuang
# di langkah terakhir. Naik bertahap ke 2160 (karakter 1426px), lalu ke sini
# setelah pemilik menyebut batas unggah situsnya 5120 KB: pada 2160 kartunya
# cuma 552 KB, jadi 89% kuota menganggur tanpa alasan.
#
# 2608x3260, BUKAN kanvas native 2613x3264: 2613x5 = 13065 sedangkan
# 3264x4 = 13056, jadi native bukan 4:5 dan kartunya akan sedikit berubah
# bentuk di situs. Ini 4:5 persis terbesar yang muat di dalam kanvas.
# Dijaga oleh cek 'ekspor tidak membuang hasil upscaler'.
PUTIH = (255, 255, 255, 255)

# (x, y, lebar, tinggi)
JENDELA_UTAMA = (130, 165, 2353, 2521)

# Urutan KIRI KE KANAN: item/1.png ke slot terkiri, item/4.png ke slot terkanan.
# Catatan: grup lapisan di PSD bernomor lain (1 di x484, 2 di x128), tapi orang
# yang menamai berkasnya 1..4 mengharapkan urutan yang ia lihat. Kalau setelah
# dilihat ternyata pemilik memang mengharapkan urutan PSD, tukar dua yang pertama.
SLOT_ITEM = ((128, 2761, 324, 327), (484, 2761, 324, 327),
             (1803, 2761, 324, 327), (2159, 2761, 324, 327))

ISIAN_KODE = (368, 2322, 563, 155)
ISIAN_DETAIL = (1683, 2322, 563, 155)
ISIAN_TINGKAT = (1058, 2736, 497, 137)

JENDELA_SLIDE = ((223, 665, 2154, 1005), (223, 1720, 2154, 1005))

# 92px diukur, bukan ditebak: "750.000" dalam Orbitron Bold jadi 466x67, muat di
# jatah 484x133 (563x155 dikurangi JEDA). Pada 96px lebarnya 485 — meleset satu
# piksel, dan setiap harga akan menyusut sendiri tanpa alasan yang terlihat.
UKURAN_ANGKA = 92
UKURAN_TINGKAT = 64


def _tempel(kanvas: Image.Image, im: Image.Image, kotak) -> None:
    x, y, lebar, tinggi = kotak
    isi = gambar.skala_menutup(im, lebar, tinggi)
    kanvas.paste(isi, (x, y), isi)


# Ambang peringatan potongan. Poster mentah Gemini keluar tegak 0,59 sementara
# jendela utama 0,93 — diukur 8 Agu, itu membuang 37% tingginya, cukup untuk
# memenggal kepala atau memotong kaki. Perkakas tetap merakit kartunya (pemilik
# yang berhak memutuskan), tapi tidak boleh diam.
AMBANG_POTONGAN = 0.15


def potongan_terbuang(im: Image.Image, kotak) -> float:
    """Berapa bagian gambar yang hilang saat dipaksa menutup `kotak`. 0..1."""
    _, _, lebar, tinggi = kotak
    faktor = max(lebar / im.width, tinggi / im.height)
    lebar_baru, tinggi_baru = im.width * faktor, im.height * faktor
    if tinggi_baru > tinggi:
        return (tinggi_baru - tinggi) / tinggi_baru
    return (lebar_baru - lebar) / lebar_baru if lebar_baru > lebar else 0.0


def _bingkai(aset: Path, nomor: int) -> Image.Image:
    berkas = Path(aset) / f'template-{nomor}.png'
    if not berkas.is_file():
        raise FileNotFoundError(f'berkas template tidak ada: {berkas}')
    return Image.open(berkas).convert('RGBA')


def rakit_kartu_utama(akun, poster: Image.Image, aset: Path,
                      tulis_teks: bool = True) -> Image.Image:
    """Kartu utama: poster di jendela besar, empat ikon item, tiga isian teks."""
    aset = Path(aset)
    kanvas = Image.new('RGBA', KANVAS, (0, 0, 0, 0))

    _tempel(kanvas, poster, JENDELA_UTAMA)
    for kotak, berkas in zip(SLOT_ITEM, akun.item):
        _tempel(kanvas, Image.open(berkas), kotak)

    kanvas = Image.alpha_composite(kanvas, _bingkai(aset, 1))

    if tulis_teks:
        orbitron = str(aset / 'Orbitron.ttf')      # font variabel, bobot dipilih saat dipakai
        poppins = str(aset / 'Poppins-Bold.ttf')   # sudah Bold, tanpa variasi
        gambar.teks_di_kotak(kanvas, ISIAN_KODE, akun.kode, orbitron, PUTIH,
                             UKURAN_ANGKA, variasi='Bold')
        gambar.teks_di_kotak(kanvas, ISIAN_DETAIL, akun.harga, orbitron, PUTIH,
                             UKURAN_ANGKA, variasi='Bold')
        gambar.teks_di_kotak(kanvas, ISIAN_TINGKAT, akun.label_tingkat,
                             poppins, PUTIH, UKURAN_TINGKAT)

    return kanvas


def pasangkan(berkas):
    """Bagi daftar berkas jadi pasangan dua-dua.

    Jumlah kartu slide berbeda antar akun — akun mahal butuh lebih banyak layar
    untuk dipamerkan — jadi jumlahnya tidak dipatok. Jumlah ganjil sudah ditolak
    di antrean.py sebelum sampai sini.
    """
    return [berkas[i:i + 2] for i in range(0, len(berkas), 2)]


def rakit_kartu_slide(pasangan, aset: Path) -> Image.Image:
    """Kartu slide: dua screenshot mentah pada dua jendela lanskap."""
    if len(pasangan) != 2:
        raise ValueError(
            f'kartu slide butuh tepat 2 gambar, diberi {len(pasangan)} — '
            f'Template 2 punya dua jendela dan jendela yang menganga lebih '
            f'buruk daripada kartu yang tidak jadi')

    kanvas = Image.new('RGBA', KANVAS, (0, 0, 0, 0))
    for kotak, berkas in zip(JENDELA_SLIDE, pasangan):
        _tempel(kanvas, Image.open(berkas), kotak)

    return Image.alpha_composite(kanvas, _bingkai(aset, 2))


def petak_di_balik_label(gambar_poster: Image.Image, isian) -> Optional[Image.Image]:
    """Potongan poster yang akan berada TEPAT di belakang tulisan label.

    Letak tulisannya dibaca dari artwork template, bukan diketik ulang sebagai
    angka kedua: kalau desainnya digeser, pemeriksaan ikut bergeser sendiri.
    Mengembalikan None kalau posternya tidak menutupi daerah itu.
    """
    x, y, lebar, _ = isian
    seni = Image.open(Path(__file__).parent / 'aset' / 'template-1.png').convert('RGBA')
    kotak = seni.crop((x, y - 160, x + lebar, y)).getchannel('A').getbbox()
    if kotak is None:
        return None

    jx, jy, jw, jh = JENDELA_UTAMA
    # Poster diskalakan menutupi jendela, jadi ruangnya sama dengan ruang jendela.
    px0, py0 = x + kotak[0] - jx, y - 160 + kotak[1] - jy
    px1, py1 = x + kotak[2] - jx, y - 160 + kotak[3] - jy
    sx = gambar_poster.width / jw
    sy = gambar_poster.height / jh
    petak = (round(px0 * sx), round(py0 * sy), round(px1 * sx), round(py1 * sy))
    if petak[0] >= petak[2] or petak[1] >= petak[3]:
        return None
    if petak[2] > gambar_poster.width or petak[3] > gambar_poster.height:
        return None
    return gambar_poster.crop(petak)


def ekspor(kanvas: Image.Image, tujuan: Path) -> None:
    """Kecilkan ke ukuran web dan simpan sebagai WebP.

    Dikonversi ke RGB: seluruh kanvas sudah buram setelah bingkai ditempel,
    jadi menyimpan saluran alfa hanya menambah ukuran berkas.
    """
    Path(tujuan).parent.mkdir(parents=True, exist_ok=True)
    kecil = kanvas.resize(EKSPOR, Image.Resampling.LANCZOS)
    kecil.convert('RGB').save(tujuan, 'WEBP', quality=EKSPOR_MUTU, method=6)

    # Berkas yang melewati batas situs sama sekali tidak berguna, dan
    # penyebabnya hampir selalu setelan (ukuran atau mutu) — jadi ia akan
    # mengenai SEMUA kartu, bukan satu. GalatFatal, sebaris dengan prasyarat
    # lain: lebih baik berhenti sekarang daripada memberi tiga puluh berkas
    # yang baru ketahuan ditolak saat diunggah satu per satu.
    besar = Path(tujuan).stat().st_size / 1024
    if besar > BATAS_UNGGAH_KB:
        raise antrean.GalatFatal(
            f'{Path(tujuan).name} berukuran {besar:.0f} KB, melewati batas unggah '
            f'situs {BATAS_UNGGAH_KB} KB. Turunkan EKSPOR atau EKSPOR_MUTU di '
            f'mesin/template.py.')
