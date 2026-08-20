"""Baca struktur folder antrean dan ubah jadi objek Akun.

Modul ini tidak menggambar apa pun. Tugasnya cuma satu: memutuskan folder mana
yang layak dirakit dan folder mana yang tidak, beserta alasannya.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

# Nilai kolom `akuns.tier`. Disalin dari system/app/Support/TierAkun.php —
# 'premium' TAMPIL sebagai 'Sultan' karena riset keyword, tapi nilai
# databasenya tidak ikut berubah. Nama folder mengikuti nilai database supaya
# tidak lahir peta kedua yang bisa berselisih dengan yang di PHP.
LABEL_TINGKAT = {'pelajar': 'Pelajar', 'reguler': 'Reguler', 'premium': 'Sultan'}
# Diturunkan dari LABEL_TINGKAT, bukan ditulis ulang: kalau ditulis terpisah,
# menambah satu tingkat ke tuple ini saja bikin foldernya lolos validasi lalu
# label_tingkat() baru meledak KeyError di tengah render — jauh dari titik
# salahnya.
TINGKAT_SAH = tuple(LABEL_TINGKAT)

EKSTENSI = ('.png', '.jpg', '.jpeg', '.webp')

JUMLAH_ITEM = 4
JUMLAH_KARAKTER = 3


class GalatFatal(Exception):
    """Keadaan yang membuat seluruh jalannya harus berhenti, bukan dilewati.

    Dipakai untuk salah pasang — nama folder tingkat yang keliru, aset hilang,
    kode akun dobel. Melewati satu folder karena isinya kurang itu wajar;
    melanjutkan dengan struktur yang salah berarti 30 kartu keluar salah semua.
    """


class GalatAkun(Exception):
    """Keadaan yang menggagalkan SATU akun saja, bukan seluruh jalannya.

    Dipakai saat sebuah folder lolos `_periksa` (validasi struktur) tapi tetap
    gagal saat benar-benar dirakit — mis. lolos karena punya karakter/ lengkap,
    tapi ternyata tidak ada poster.png dan Perkakas B (poster.py) belum ada.
    Akun lain di antrean tidak ikut bertanggung jawab atas nasib satu ini;
    29 akun sehat lainnya tetap harus jadi malam itu juga.
    """


@dataclass
class Akun:
    kode: str
    tingkat: str
    harga: str
    folder: Path
    karakter: List[Path] = field(default_factory=list)
    item: List[Path] = field(default_factory=list)
    slide: List[Path] = field(default_factory=list)
    poster: Optional[Path] = None
    # Screenshot layar Fashion di akar folder akun. Kalau ada, item/ jadi HASIL
    # (dipotong ulang tiap lari), bukan masukan — supaya satu klik cukup.
    layar_item: Optional[Path] = None
    # Petak mana yang diambil, dari baris "item:" di info.txt. Kosong = empat
    # petak pertama yang utuh.
    pilihan_item: List[int] = field(default_factory=list)
    peringatan: List[str] = field(default_factory=list)

    @property
    def label_tingkat(self) -> str:
        return LABEL_TINGKAT[self.tingkat]


def _kunci_alami(berkas: Path):
    """Urutkan 1, 2, 10 — bukan 1, 10, 2.

    Akun mahal butuh lebih banyak layar slide, jadi 10+ berkas bukan kasus
    langka. Dengan urutan abjad biasa, `10.png` menyusup di antara `1.png` dan
    `2.png`, dan pasangan kartu slide jadi acak — cacat yang cuma muncul pada
    akun paling mahal, yang paling tidak boleh salah.
    """
    return [int(bagian) if bagian.isdigit() else bagian.lower()
            for bagian in re.split(r'(\d+)', berkas.stem)]


def _gambar_di(folder: Path) -> List[Path]:
    if not folder.is_dir():
        return []
    # Menyalin screenshot lewat exFAT atau langsung dari HP meninggalkan
    # "._1.png" AppleDouble di sebelah "1.png" — tidak kelihatan di Finder,
    # tapi ikut kehitung sampai jumlahnya dobel dan folder yang sebenarnya
    # sehat dilewati dengan alasan yang tidak bisa dicek pemilik.
    return sorted((b for b in folder.iterdir()
                   if b.is_file() and not b.name.startswith('.')
                   and b.suffix.lower() in EKSTENSI),
                  key=_kunci_alami)


def _baca_pilihan_item(folder: Path) -> List[int]:
    """Baris `item: 3 4 6 7` di info.txt — petak mana yang dipakai.

    Kosong berarti empat petak pertama yang utuh. Angka di luar jangkauan
    dibiarkan lewat: pemotongnya yang menolak, dengan pesan yang menyebut
    berapa petak yang sebenarnya ada.
    """
    berkas = folder / 'info.txt'
    if not berkas.is_file():
        return []
    try:
        isi = berkas.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return []
    for baris in isi.splitlines():
        b = baris.strip()
        if b.lower().startswith('item:'):
            return [int(x) for x in b.split(':', 1)[1].split() if x.isdigit()]
    return []


def _layar_item(folder: Path) -> Tuple[Optional[Path], Optional[str]]:
    """Screenshot layar Fashion yang tergeletak di akar folder akun.

    Dibedakan dari poster.png lewat namanya saja — apa pun gambar lain di akar
    dianggap sumber ikon. Dua atau lebih berarti pemilik tidak bisa dimintai
    tebakan mana yang benar, jadi dilaporkan, bukan ditebak.
    """
    kandidat = [b for b in _gambar_di(folder) if b.name.lower() != 'poster.png']
    if not kandidat:
        return None, None
    if len(kandidat) > 1:
        nama = ', '.join(b.name for b in kandidat)
        return None, (f'ada {len(kandidat)} gambar di akar folder akun ({nama}) — '
                      f'sisakan satu saja, yaitu screenshot layar Fashion')
    return kandidat[0], None


def _baca_harga(folder: Path) -> Tuple[Optional[str], Optional[str]]:
    """Kembalikan (harga, None) kalau terbaca, atau (None, alasan) kalau tidak.

    Tiga alasan dibedakan sengaja: file tidak ada, file ada tapi tidak punya
    baris "harga:", dan baris "harga:" ada tapi nilainya kosong. Pemilik yang
    mengetik info.txt dengan tangan butuh tahu yang mana — pesan gabungan
    cuma bikin ia menebak.
    """
    berkas = folder / 'info.txt'
    if not berkas.is_file():
        return None, 'info.txt tidak ada'

    try:
        isi = berkas.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # TextEdit di macOS masih bisa menyimpan sebagai UTF-16 kalau
        # pemiliknya tidak sengaja pilih "Unicode (UTF-8)". Tanpa tangkapan
        # ini, satu info.txt salah encoding menjatuhkan seluruh jalannya
        # dengan traceback mentah, bukan cuma melewatkan satu folder.
        return None, ('info.txt tidak terbaca sebagai teks UTF-8 — simpan ulang '
                       'lewat TextEdit dengan encoding "Unicode (UTF-8)"')

    for baris in isi.splitlines():
        baris = baris.strip()   # baris "  harga: 750.000" tetap harus kena
        if baris.lower().startswith('harga:'):
            nilai = baris.split(':', 1)[1].strip()
            if not nilai:
                return None, 'info.txt punya baris "harga:" tapi nilainya kosong'
            return nilai, None

    return None, 'info.txt tidak punya baris "harga:"'


def _periksa(folder: Path, tingkat: str) -> Tuple[Optional[Akun], Optional[str]]:
    """Kembalikan (akun, None) kalau layak, atau (None, alasan) kalau dilewati."""
    karakter = _gambar_di(folder / 'karakter')
    item = _gambar_di(folder / 'item')
    slide = _gambar_di(folder / 'slide')
    poster = folder / 'poster.png'
    poster = poster if poster.is_file() else None

    layar, alasan_layar = _layar_item(folder)
    if alasan_layar:
        return None, alasan_layar

    # Dengan layar Fashion, item/ diisi ulang tiap lari — isinya sekarang tidak
    # menentukan apa pun. Tanpa layar Fashion, ia masukan dan harus tepat empat.
    if layar is None and len(item) != JUMLAH_ITEM:
        return None, (f'item/ berisi {len(item)} gambar dan tidak ada screenshot '
                      f'layar Fashion di folder akun — butuh tepat {JUMLAH_ITEM}, '
                      f'atau taruh screenshot Fashion-nya biar dipotong otomatis')

    if not slide:
        return None, 'slide/ kosong — tidak ada yang membuktikan skinnya ada'

    if len(slide) % 2:
        return None, (f'slide/ berisi {len(slide)} berkas, harus genap '
                      f'(dua per kartu) — tambah atau kurangi satu')

    if poster is None and len(karakter) != JUMLAH_KARAKTER:
        return None, (f'karakter/ berisi {len(karakter)} gambar dan tidak ada '
                      f'poster.png — butuh tepat {JUMLAH_KARAKTER}, atau sediakan poster.png')

    harga, alasan_harga = _baca_harga(folder)
    if harga is None:
        return None, alasan_harga

    peringatan = []
    if poster is None and len(karakter) > 1:
        # Berkas karakter yang isinya sama persis menghasilkan poster berisi
        # satu karakter yang dikloning tiga kali. Ini salah isi antrean, bukan
        # salah mesin — tapi tanpa peringatan, pemilik akan menyangka perlakuan
        # gambarnyalah yang gagal. Diukur 8 Agu 2026: ketiga berkas di 666
        # ternyata md5 identik, bernama copy dan copy 2.
        # Gerbang `poster is None`: begitu akun punya poster.png sendiri,
        # _poster_untuk (rakit.py) mengembalikannya langsung tanpa pernah
        # memanggil poster.rakit() — karakter/ tidak dibaca sama sekali dalam
        # jalur itu, jadi memperingatkan kembar di sini adalah peringatan palsu.
        sidik = [hashlib.md5(b.read_bytes()).hexdigest() for b in karakter]
        if len(set(sidik)) < len(sidik):
            peringatan.append(
                'karakter/ berisi berkas yang isinya identik — posternya akan '
                'memajang karakter yang sama lebih dari sekali')

    return Akun(kode=folder.name, tingkat=tingkat, harga=harga, folder=folder,
                karakter=karakter, item=item, slide=slide, poster=poster,
                layar_item=layar, pilihan_item=_baca_pilihan_item(folder),
                peringatan=peringatan), None


def baca(akar: Path) -> Tuple[List[Akun], List[Tuple[str, str]]]:
    """Jelajahi `akar/<tingkat>/<kode>/` dan pilah yang layak dari yang tidak."""
    akar = Path(akar)
    if not akar.is_dir():
        raise GalatFatal(f'folder antrean tidak ada: {akar}')

    daftar: List[Akun] = []
    dilewati: List[Tuple[str, str]] = []

    # Skenario yang sama dengan companion AppleDouble (._1.png di _gambar_di):
    # menyalin lewat exFAT atau langsung dari HP juga menaruh folder titik
    # tak kasat mata — .Trashes, .Spotlight-V100 — di sebelah folder akun
    # sungguhan. Tanpa saringan ini keduanya lolos sampai ke _periksa dan
    # dilaporkan sebagai akun DILEWATI ("item/ berisi 0 gambar"), padahal
    # bukan akun sama sekali.
    for folder_tingkat in sorted(p for p in akar.iterdir()
                                 if p.is_dir() and not p.name.startswith('.')):
        tingkat = folder_tingkat.name
        if tingkat not in TINGKAT_SAH:
            raise GalatFatal(
                f'nama folder tingkat "{tingkat}" tidak dikenal. '
                f'Pakai nilai database: {", ".join(TINGKAT_SAH)}. '
                f'"Sultan" itu label tampilan untuk premium, bukan nama folder.')

        for folder_akun in sorted(p for p in folder_tingkat.iterdir()
                                  if p.is_dir() and not p.name.startswith('.')):
            akun, alasan = _periksa(folder_akun, tingkat)
            if akun is None:
                dilewati.append((f'{tingkat}/{folder_akun.name}', alasan))
            else:
                daftar.append(akun)

    # Nama berkas keluaran cuma pakai kode ("5001-utama.webp"), tidak pernah
    # tingkatnya. premium/5001 dan reguler/5001 akan menulis berkas yang
    # sama — satu diam-diam menimpa yang lain, dan ringkasan tetap melaporkan
    # angka yang seolah benar. Ini salah pasang lintas folder, bukan cacat
    # satu folder, jadi menghentikan seluruh jalannya seperti nama tingkat
    # yang keliru.
    folder_dari: dict = {}
    for akun in daftar:
        asal = f'{akun.tingkat}/{akun.kode}'
        if akun.kode in folder_dari:
            raise GalatFatal(
                f'kode akun "{akun.kode}" dobel di {folder_dari[akun.kode]} dan '
                f'{asal} — nama berkas keluaran cuma pakai kode, jadi salah satu '
                f'akan menimpa punya yang lain. Ganti salah satu kode atau '
                f'pindahkan foldernya.')
        folder_dari[akun.kode] = asal

    return daftar, dilewati
