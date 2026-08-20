#!/usr/bin/env python3
"""Perakit materi listing akun — Perkakas A.

Pakai:
    python3 mesin/rakit.py antrean/ siap-upload/
    python3 mesin/rakit.py antrean/ siap-upload/ --ulang

Membaca antrean/<tingkat>/<kode>/ lalu menghasilkan kartu siap unggah.
Folder yang isinya kurang DILEWATI dan tercatat di ringkasan akhir; salah
pasang (nama tingkat keliru, aset hilang) MENGHENTIKAN seluruh jalannya.

Akun yang kartunya sudah ada di siap-upload/<kode>/ tidak dibuat ulang.
--ulang mengabaikan itu dan merakit semuanya dari awal — yang dibutuhkan
setiap kali MESINnya berubah, karena penandanya cuma melihat folder
keluaran dan tidak tahu apa-apa soal setelan poster.py atau isi latar/.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))

import antrean
import template

ASET_BAWAAN = Path(__file__).parent / 'aset'


def _galat_pemotong(sistem: str, biner_ada: bool) -> Optional[str]:
    """Alasan kenapa Perkakas B tak bisa merakit poster di mesin ini, atau None.

    Dipisah dari preflight supaya kedua cabangnya bisa diuji tanpa mesin
    Windows dan tanpa menghapus biner di mesin macOS.

    Di luar macOS keberadaan berkasnya TIDAK diperiksa, dan itu disengaja:
    biner Mach-O yang kebawa lewat sinkronisasi folder tetap tidak bisa
    dijalankan di sana, dan Vision-nya sendiri memang tidak ada. Meloloskannya
    cuma memindahkan kegagalan ke dalam — per akun, dengan pesan buram dari
    subprocess yang menolak jalan.
    """
    if sistem != 'darwin':
        return ('jalur karakter/ butuh pemotong Vision yang cuma ada di macOS. '
                'Di mesin ini, sediakan poster.png di tiap folder akun yang '
                'belum punya — selain itu perkakasnya berjalan penuh.')
    if not biner_ada:
        import poster
        return (f'biner pemotong belum dikompilasi: {poster.POTONG}. '
                f'Jalankan: swiftc -O -o {poster.POTONG} {poster.POTONG}.swift')
    return None


def _poster_untuk(akun, aset: Path, catat: Optional[List[str]] = None) -> Image.Image:
    """Pakai poster.png kalau ada; kalau tidak, minta Perkakas B merakitnya.

    Perkakas B diimpor di dalam fungsi, bukan di puncak berkas: Perkakas A harus
    tetap jalan penuh sebelum B ada, dan tetap jalan kalau pemilik memutuskan B
    tidak layak dipakai untuk karakter bersayap.

    `catat`, kalau diberikan, diteruskan ke poster.rakit supaya karakter yang
    terpotong tepi panggung tercatat — tidak relevan kalau akun sudah punya
    poster.png sendiri, karena itu bukan hasil rakitan Perkakas B.
    """
    if akun.poster is not None:
        return Image.open(akun.poster).convert('RGBA')

    try:
        import poster
    except ImportError:
        # Per-akun, bukan GalatFatal: folder ini lolos _periksa (karakter/
        # lengkap), tapi Perkakas B belum ada untuk merakit posternya. 29
        # akun sehat lain di antrean tidak boleh ikut mati gara-gara satu ini.
        raise antrean.GalatAkun(
            f'{akun.kode} tidak punya poster.png dan Perkakas B (poster.py) '
            f'belum ada. Taruh poster.png di folder akun itu, atau selesaikan '
            f'poster.py lebih dulu.')

    return poster.rakit(akun, aset, catat)


def _sudah_jadi(folder_akun: Path) -> bool:
    """Benarkah folder keluaran ini berisi hasil yang sudah selesai?

    Yang dihitung ISInya, bukan keberadaan foldernya. Lari yang mati di tengah
    meninggalkan folder kosong, dan kalau keberadaan folder yang jadi penanda,
    akun itu tidak akan pernah jadi lagi sampai pemilik menghapusnya sendiri —
    padahal ia tidak punya cara tahu foldernya kosong di antara tiga puluh yang
    lain.

    Yang dilihat cuma folder keluaran, bukan isi antrean dan bukan mesinnya.
    Konsekuensinya disengaja dan dipilih pemilik 14 Agu: mengganti screenshot
    atau menyetel poster.py TIDAK menyebar sendiri ke kartu yang terlanjur
    jadi. Buang folder akunnya, atau pakai --ulang.
    """
    return any(folder_akun.glob('*.webp'))


def jalankan(akar: Path, tujuan: Path, aset: Path = ASET_BAWAAN,
             ulang: bool = False,
             ) -> Tuple[List[Path], List[Tuple[str, str]], List[Tuple[str, str]], List[str]]:
    aset = Path(aset)
    for wajib in ('template-1.png', 'template-2.png',
                  'Orbitron.ttf', 'Poppins-Bold.ttf'):
        if not (aset / wajib).is_file():
            raise antrean.GalatFatal(f'aset wajib tidak ada: {aset / wajib}')

    daftar, dilewati = antrean.baca(akar)

    # Prasyarat Perkakas B baru bisa dicek SESUDAH antrean dibaca: yang
    # dibutuhkan tergantung tingkat mana yang ada dan akun mana yang tak
    # punya poster.png. Tetap salah pasang, jadi tetap GalatFatal — biner
    # belum dikompilasi (bawaan checkout baru, sengaja digitignore) atau
    # latar tingkat yang hilang bukan cacat SATU folder, dan membiarkannya
    # bocor lewat except per-akun mengubur satu masalah nyata di balik N
    # baris "DILEWATI" yang identik.
    perlu_b = {a.tingkat for a in daftar if a.poster is None}
    if perlu_b:
        try:
            import poster
        except ImportError:
            # poster.py sendiri belum ada — bukan cuma biner atau latarnya.
            # Prasyarat B (biner + latar/<tingkat>.png) tidak relevan untuk
            # modul yang tak bisa diimpor, jadi TIDAK diperiksa di sini.
            # _poster_untuk sudah menjaga invariannya sendiri per akun (lihat
            # docstring-nya): akun berposter.png sendiri tetap jalan, akun
            # yang butuh Perkakas B dilewati lewat GalatAkun — bukan proses
            # ini yang mati total gara-gara modul yang memang belum ada.
            pass
        else:
            galat = _galat_pemotong(sys.platform, poster.POTONG.exists())
            if galat is not None:
                raise antrean.GalatFatal(galat)
            for tingkat in sorted(perlu_b):
                berkas = poster.LATAR_BAWAAN / f'{tingkat}.png'
                if not berkas.is_file():
                    raise antrean.GalatFatal(f'aset wajib tidak ada: {berkas}')

    tujuan = Path(tujuan)
    dibuat: List[Path] = []
    peringatan: List[Tuple[str, str]] = []
    sudah_ada: List[str] = []

    for akun in daftar:
        # Diputuskan SEBELUM apa pun dikerjakan, bukan sesudah: ikon item juga
        # tidak dipotong ulang, dan itu bagian termahal dari akun yang punya
        # screenshot Fashion.
        #
        # Daftarnya sendiri, terpisah dari `dilewati`. Keduanya beda arti dan
        # menuntut tindakan berbeda: DILEWATI berarti folder antreannya kurang
        # dan harus pemilik perbaiki, yang ini berarti kartunya memang sudah
        # ada dan tidak butuh apa-apa. Digabung, sepuluh baris "sudah ada"
        # menenggelamkan satu folder yang sungguh rusak.
        if not ulang and _sudah_jadi(tujuan / akun.kode):
            sudah_ada.append(f'{akun.tingkat}/{akun.kode}')
            continue

        # Satu akun boleh gagal di sini karena alasan yang cuma ketahuan saat
        # DIRAKIT, bukan saat divalidasi — poster.png tidak ada, atau berkas
        # gambar yang rusak (mis. screenshot nol byte yang masih disalin dari
        # HP) bikin Pillow melempar UnidentifiedImageError. Kalau dibiarkan
        # menembus, satu akun cacat menjatuhkan seluruh sisa antrean; lebih
        # baik kartu yang sudah sempat jadi tetap dilaporkan dan akun berikut
        # tetap dicoba. Prefiks "gagal saat merakit" membedakannya dari alasan
        # dilewati saat validasi (antrean._periksa) — pemilik menanganinya beda:
        # yang ini berarti isinya sudah lengkap tapi rusak/kurang, bukan kurang.
        # Ditampung lokal, bukan langsung ke `dibuat`/`peringatan` bersama:
        # template.rakit_kartu_utama baru membuka ikon item DI DALAM dirinya,
        # sesudah baris peringatan di bawah ini sudah siap ditulis. Kalau
        # ikonnya rusak, exception meletus SESUDAH peringatan itu "commit" —
        # akun yang builds-nya gagal jadi nongol di PERINGATAN ("kartunya
        # tetap dibuat") padahal DILEWATI. Baris atau berkas yang diklaim
        # untuk akun yang lalu gagal membuat ringkasan berbohong soal apa yang
        # sungguh ada di disk. try/except/else: cuma commit ke daftar bersama
        # kalau seluruh badan akun ini kelar tanpa exception.
        dibuat_akun: List[Path] = []
        peringatan_akun: List[Tuple[str, str]] = []
        try:
            # Ikon dipotong ulang tiap lari kalau screenshot Fashion-nya ada.
            # item/ jadi HASIL, bukan masukan — supaya satu klik cukup, dan
            # supaya mengubah baris "item:" di info.txt langsung berlaku tanpa
            # perlu menghapus isi item/ dulu.
            if akun.layar_item is not None:
                import potong_item
                folder_item = akun.folder / 'item'
                for lama_item in folder_item.glob('*'):
                    if lama_item.is_file():
                        lama_item.unlink()
                # Tanpa baris "item:" di info.txt, empat petak pertama yang
                # utuh. Bukan semua petak: item/ isinya harus persis yang dipakai,
                # kalau tidak lari berikutnya melihat tujuh berkas dan bingung.
                pilihan = akun.pilihan_item or [1, 2, 3, 4]
                if len(pilihan) != 4:
                    raise ValueError(
                        f'baris "item:" di info.txt menyebut {len(pilihan)} petak, '
                        f'harus tepat 4')
                akun.item = potong_item.potong(akun.layar_item, folder_item, pilihan)

            # Satu folder per akun. Dengan tiga puluh akun, kartu yang berserak
            # di satu daftar berarti memungut berkas satu akun di antara berkas
            # akun lain setiap kali mengunggah. Nama berkasnya sengaja tetap
            # berprefiks kode: yang terlanjur diseret keluar folder masih punya
            # identitas.
            #
            # Foldernya tidak dibuat di sini — template.ekspor sudah
            # membuat induk berkasnya. Satu tempat yang membuat folder, bukan
            # dua yang harus sepakat.
            folder_akun = tujuan / akun.kode

            # Sisa lari sebelumnya harus dibuang dulu: jumlah kartu slide bisa
            # BERKURANG antar lari (screenshot dihapus, atau lari sebelumnya
            # mati di tengah jalan), dan berkas lebih yang tertinggal ikut
            # terunggah walau ringkasan tidak pernah menyebutnya. `glob` pada
            # folder tujuan yang belum ada mengembalikan kosong, jadi lari
            # pertama tidak butuh penjaga tambahan.
            #
            # Pola datar di akar ikut disapu. Sampai 14 Agu kartu ditulis
            # langsung ke akar tujuan, jadi tanpa baris itu lari pertama
            # sesudah perubahan ini meninggalkan dua salinan di dua tempat —
            # dan tidak ada yang memberitahu mana yang basi. Ia menyapu apa pun
            # yang cocok, bukan sekali lalu ditandai selesai: pemilik bisa saja
            # memulihkan folder siap-upload lama dari cadangan kapan pun.
            for lama in list(folder_akun.glob('*.webp')) \
                    + list(tujuan.glob(f'{akun.kode}-*.webp')):
                lama.unlink()

            for pesan in akun.peringatan:
                peringatan_akun.append((akun.kode, pesan))

            catat_potongan: List[str] = []
            gambar_poster = _poster_untuk(akun, aset, catat_potongan)
            for pesan in catat_potongan:
                peringatan_akun.append((akun.kode, pesan))

            # Label template ditulis putih dan di-composite PALING AKHIR, jadi
            # ia tidak pernah tertutup karakter — tapi kontrasnya bisa hilang
            # kalau yang kebetulan berada di belakangnya terang. Itu yang
            # sungguh terjadi pada 777: teks putih di atas sepatu merah-putih.
            # Diperiksa di sini, bukan di poster.py, karena letak labelnya
            # milik template DAN karena ini berlaku juga untuk poster.png
            # buatan AI, yang tidak pernah lewat Perkakas B.
            try:
                import poster as _pemeriksa_kontras
            except ImportError:
                _pemeriksa_kontras = None
            if _pemeriksa_kontras is not None:
                for nama_label, isian in (('Kode Akun', template.ISIAN_KODE),
                                          ('Detail', template.ISIAN_DETAIL)):
                    petak = template.petak_di_balik_label(gambar_poster, isian)
                    if petak is not None and \
                            _pemeriksa_kontras._latar_label_terlalu_terang(petak):
                        peringatan_akun.append((
                            akun.kode,
                            f'latar di belakang tulisan "{nama_label}" terang — '
                            f'teks putihnya bisa sulit dibaca'))

            # Poster yang rasionya jauh dari jendela akan terpotong banyak, dan
            # yang hilang justru kepala atau kaki karakter. Kartunya tetap
            # dibuat — pemilik yang berhak memutuskan layak atau tidak — tapi
            # ia harus tahu.
            buang = template.potongan_terbuang(gambar_poster, template.JENDELA_UTAMA)
            if buang > template.AMBANG_POTONGAN:
                peringatan_akun.append((
                    akun.kode,
                    f'poster {gambar_poster.width}x{gambar_poster.height} kehilangan '
                    f'{buang * 100:.0f}% saat masuk jendela — buat posternya sekitar '
                    f'{template.JENDELA_UTAMA[2]}x{template.JENDELA_UTAMA[3]}'))

            kartu = template.rakit_kartu_utama(akun, gambar_poster, aset)
            berkas = folder_akun / f'{akun.kode}-utama.webp'
            template.ekspor(kartu, berkas)
            dibuat_akun.append(berkas)

            for nomor, pasangan in enumerate(template.pasangkan(akun.slide), start=1):
                kartu = template.rakit_kartu_slide(pasangan, aset)
                berkas = folder_akun / f'{akun.kode}-slide-{nomor}.webp'
                template.ekspor(kartu, berkas)
                dibuat_akun.append(berkas)
        except antrean.GalatFatal:
            # Salah pasang ketahuan di tengah antrean (mis. lewat cabang lain
            # yang belum sempat dicek preflight) tetap harus menembus sampai
            # ke main() — kalau ditelan except Exception di bawah, satu
            # masalah lintas-akun terlapor sebagai N baris DILEWATI dan
            # proses keluar 0 seolah sehat.
            raise
        except Exception as e:
            # Celah yang sengaja dibiarkan: kalau kartu utama sudah sempat
            # tertulis ke disk lalu kartu slide sesudahnya yang gagal, berkas
            # -utama.webp itu tetap ada secara fisik tapi tidak ikut terhitung
            # di `dibuat` (dibuat_akun dibuang bersama exception ini). Itu
            # lebih jujur daripada kebalikannya: ringkasan meng-KURANG-klaim,
            # bukan meng-LEBIH-klaim — dan berkas nyasar itu masih bisa
            # ditemukan langsung di folder tujuan kalau perlu.
            dilewati.append((f'{akun.tingkat}/{akun.kode}', f'gagal saat merakit: {e}'))
        else:
            dibuat.extend(dibuat_akun)
            peringatan.extend(peringatan_akun)

    return dibuat, dilewati, peringatan, sudah_ada


def main() -> int:
    arg = [a for a in sys.argv[1:] if a != '--ulang']
    ulang = '--ulang' in sys.argv[1:]
    if len(arg) != 2:
        print(__doc__)
        return 2

    galat = None
    dibuat, dilewati, peringatan, sudah_ada = [], [], [], []
    try:
        dibuat, dilewati, peringatan, sudah_ada = jalankan(
            Path(arg[0]), Path(arg[1]), ulang=ulang)
    except antrean.GalatFatal as e:
        galat = e

    # Ringkasan tercetak walau GalatFatal menembus: perkakas ini jalan
    # semalam tanpa pengawas, jadi kartu yang sempat jadi sebelum salah
    # pasang ketahuan tidak boleh hilang dari laporan pagi harinya.
    print(f'{len(dibuat)} berkas dibuat di {arg[1]}')
    if sudah_ada:
        print(f'\n{len(sudah_ada)} akun sudah ada, tidak dibuat ulang:')
        for nama in sudah_ada:
            print(f'  = {nama}')
        print('  (buang foldernya di siap-upload, atau jalankan dengan --ulang)')
    if peringatan:
        print(f'\n{len(peringatan)} PERINGATAN (kartunya tetap dibuat):')
        for kode, pesan in peringatan:
            print(f'  ! {kode}: {pesan}')
    if dilewati:
        print(f'\n{len(dilewati)} folder DILEWATI:')
        for nama, alasan in dilewati:
            print(f'  - {nama}: {alasan}')

    if galat is not None:
        print(f'\nBERHENTI: {galat}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
