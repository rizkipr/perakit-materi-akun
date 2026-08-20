"""Perakit poster tiga karakter — Perkakas B.

Dipakai hanya kalau folder akun tidak menyediakan poster.png. Karakter TIDAK
PERNAH digambar ulang: yang ditempel adalah piksel asli screenshot pemilik,
karena skin senjata itulah barang yang dibayar pembeli.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

# Tidak ada lingkar impor: antrean.py cuma memakai pustaka bawaan Python dan
# tidak pernah mengimpor poster. Diimpor untuk GalatFatal — kegagalan
# mengambil upscaler adalah salah pasang lintas antrean, bukan cacat satu
# folder (lihat _ambil_upscaler).
import antrean

POTONG = Path(__file__).parent / 'potong'
LATAR_BAWAAN = Path(__file__).parent.parent / 'latar'

# Tata letak. Nilainya tidak berubah antar akun, jadi konstanta di sini —
# bukan berkas konfigurasi untuk nilai yang tidak pernah disetel ulang.
TINGGI_KARAKTER = 0.72      # fraksi tinggi kanvas untuk karakter samping
# 0,60 dulu menyisakan ruang kosong lebar di atas kepala, dan kartunya terbaca
# lapang alih-alih megah. Dinaikkan bertahap 9 Agu sambil diadu dengan poster
# rujukan pemilik: 0,68, lalu 0,81 (kelewat besar — kepala mentok tepi
# jendela dan badan saling menelan), akhirnya 0,72 yang DIUKUR dari
# referensi itu sendiri: di sana karakter tengah setinggi 0,82 jendela,
# jadi TINGGI_KARAKTER = 0,82 / 1,14.
#
# Ukuran dan GARIS_DASAR TERIKAT, bukan dua setelan bebas. Karakter digambar
# dari garis dasar ke ATAS, jadi kepalanya hanya muat kalau
# TINGGI_KARAKTER x SKALA_TENGAH <= GARIS_DASAR. Itulah sebabnya poster
# rujukan menaruh kaki serendah itu — bukan pilihan gaya, tapi syarat ruang.
# Dijaga cek 'kepala karakter muat di kanvas'.
SKALA_TENGAH = 1.14         # yang tengah lebih besar supaya jadi titik pandang
GARIS_DASAR = 0.95          # fraksi tinggi kanvas tempat kaki menapak
# Sempat 0,86 lalu diturunkan ke 0,82 pada 9 Agu, dengan alasan yang ternyata
# salah paham: dikira sepatu karakter MENUTUPI kata 'Detail'. Ia tidak bisa —
# template.rakit_kartu_utama menempel poster dulu lalu meng-alpha_composite
# bingkainya DI ATAS, jadi tulisan label selalu tergambar paling akhir. Yang
# rusak waktu itu kontrasnya: teks putih di atas sepatu merah-putih yang ramai.
#
# 0,95 diukur dari poster rujukan: di sana kaki menapak di ~0,96 tinggi
# jendela. Angka ini bukan selera bebas — ia menentukan RUANG KEPALA, karena
# karakter digambar dari garis dasar ke atas. Ruang kepala = GARIS_DASAR
# dikurangi TINGGI_KARAKTER x SKALA_TENGAH; di sini 0,95 - 0,821 = 12,9%,
# yang cocok dengan ~13% yang terukur di referensi.
#
# Sempat dicoba 0,93 dengan TINGGI_KARAKTER 0,81: ruang kepalanya tinggal
# 0,7% dan kepala karakter tengah mentok tepi jendela. Cek 'kepala karakter
# punya ruang napas' menjaga supaya itu tidak terulang diam-diam.
#
# Kaki turun melewati pita label. Diperiksa mata pada 777: kedua label tetap
# terbaca penuh karena telapaknya duduk di SAMPING tulisan. Yang menjaga kasus
# buruknya peringatan kontras, bukan larangan geometris.
# POS_X dihapus 9 Agu. Ia memaku pusat tiap karakter di 0,23/0,50/0,77
# tanpa peduli lebar, sehingga celah antar karakter tidak pernah bisa
# dijamin: pada 777 jaraknya -137px, badan bertumpuk. Penggantinya ada
# di tata_letak, yang membagikan celah lalu memusatkan kelompoknya.
# Untuk pose simetris hasilnya praktis sama dengan angka lama.

# Celah latar minimum antar BADAN karakter, fraksi lebar kanvas. Diukur dari
# poster rujukan pemilik: di sana api kota terlihat jelas di sela ketiganya, dan
# itulah yang membuat mereka terbaca sebagai tiga sosok, bukan satu gumpalan.
# Yang dijamin punya celah adalah inti badan, bukan kotak-batas — lihat
# inti_alfa.
CELAH_MINIMUM = 0.038

# Batas antara BADAN dan jubah. Sebuah kolom dihitung badan kalau piksel
# pekatnya menutupi setidaknya INTI_CAKUPAN bagian tinggi kutout.
#
# Diukur 14 Agu pada FF-PELAJAR-6001: kutout karakter kiri 514x551 — rasio 0,93,
# hampir persegi — padahal badannya cuma 353px. Sisanya jubah biru mengembang
# dan bilah sabit yang menjulur mendatar. tata_letak dulu mengukur lebar dari
# kotak-batas alfa, jadi jubah itu dihitung seberat badan: ketiga karakter
# disusutkan 38% dan kartunya terbaca kerdil dengan 45% ruang kosong di atas
# kepala.
#
# Yang membedakan badan dari jubah bukan warna atau kepekatannya, melainkan
# CAKUPAN TEGAK: kolom badan terisi hampir setinggi karakter, kolom jubah dan
# senjata mendatar cuma sepotong kecil.
#
# Konsekuensinya disengaja: jubah dan ujung senjata kini boleh menyelinap di
# belakang tetangganya, bahkan keluar tepi jendela. Itu pertukaran yang dipilih
# pemilik 14 Agu — jubah terpotong sedikit lebih murah daripada tiga karakter
# yang kerdil semua.
#
# 0,30, bukan 0,10 yang dipakai sehari pertama. Angka pertama itu cukup untuk
# jubah dan bilah, tapi tidak untuk PELIHARAAN: pada FF-REGULER-6001 peliharaan
# menempel di bilah pedang karakter tengah dan menutupi 12-24% tinggi, jadi ia
# lolos sebagai badan. Slot tengah lalu memusatkan orang + peliharaan, dan
# orangnya sendiri terdorong ke kiri — kartunya terbaca tidak center.
#
# Peliharaan itu TIDAK bisa dibuang: diukur, erosi 12 piksel pun meninggalkan
# badan, pedang, dan peliharaan sebagai satu komponen tersambung, karena
# bilahnya memang masuk ke daerah peliharaan. Membuangnya berarti memotong
# pedang, dan skin senjata adalah barang yang dibayar pembeli.
#
# Kolom badan di bahan yang sama menutupi 37-74%, jadi 0,30 duduk di jurang
# yang lebar di antara keduanya — masih menerima kaki yang mengangkang dan
# tangan yang terentang, yang selalu jauh di atas sepertiga tinggi.
INTI_CAKUPAN = 0.30
INTI_PEKAT = 128            # alfa minimum sebuah piksel dihitung pekat

WARNA_BAYANGAN = (0, 0, 0, 150)
RONA_HANGAT = (255, 140, 40, 38)

# Diukur 8 Agu 2026 pada tiga screenshot lobi asli pemilik: potongan Vision
# membawa serambut tipis warna latar lobi di pinggirnya — samar di latar
# gelap, tapi akan terbaca sebagai halo begitu karakter dipindah ke panggung
# lain. Dua piksel adalah batas atas yang aman: cukup untuk membuang
# serambut, belum cukup untuk memutus detail tipis (laras senjata, helai
# rambut) — diverifikasi mata pada potongan nyata sebelum dipakai.
KIKIS_PIKSEL = 2

# Latar diblur dan diredupkan bukan demi gaya, tapi karena mata menilai
# ketajaman secara relatif. Latar foto beresolusi penuh membuat karakter yang
# piksel aslinya cuma 226x570 selalu terbaca burik di sebelahnya, berapa pun
# angka pembesarannya. Menghentikan perbandingan itu memberi perbaikan lebih
# besar daripada mempertajam karakternya. Diukur 8 Agu 2026 pada bahan 666.
LATAR_BLUR = 7        # piksel, pada kanvas 2353 x 2521
LATAR_REDUP = 0.88    # 0,80 membuat lokasi latar hilang jadi lumpur

# Structure dan sharpen adalah dua operasi berbeda, bukan pengulangan. Radius
# besar berkadar sedang mengangkat kontras lokal frekuensi menengah — tekstur
# kain, lipatan, ukiran senjata — tanpa menyentuh tepi siluet, jadi tidak
# melahirkan halo. Radius kecil berkadar tinggi menegaskan tepinya. Editor
# Free Fire memakai keduanya; memakai sharpen saja terbukti kurang berisi
# saat dibandingkan berdampingan pada bahan 666.
STRUKTUR = (28, 60)        # radius, persen; ambangnya selalu 0
UNSHARP = (2.5, 130, 3)    # radius, persen, ambang
# Ambang 3 menahan bidang gelap yang rata agar tidak ikut dipertajam. Varian
# beambang 2 dan berkadar 185 membuat sweter hitam berbintik derau.
KONTRAS = 1.14
SATURASI = 1.20

# Bloom: cahaya yang KELUAR dari benda terang-jenuh. Inilah yang membedakan
# kartu yang terbaca "mewah" dari kartu yang cuma tajam — di Free Fire, skin
# senjata memang memancar, dan tanpa ini karakter terlihat ditempel di atas
# latar alih-alih berdiri di dalamnya. Dua ambang, bukan satu: terang SAJA
# akan membuat kulit dan kain putih ikut berkabut, jadi kejenuhan warna ikut
# disyaratkan. Diadu 9 Agu pada 777 di atas latar kota terbakar; takaran ini
# ("kuat") dipilih pemilik karena senjata menyala tanpa kehilangan bentuknya —
# takaran di atasnya menelan ujung senjata api sampai skinnya tak terbaca.
BLOOM_AMBANG = 150      # kecerahan minimum sebuah piksel boleh ikut menyala
BLOOM_JENUH = 95        # selisih kanal minimum; menahan kulit dan abu netral
# 95, bukan 60. Diukur: kulit terang (205,170,140) berkejenuhan 65 dan pada
# ambang 60 ia menyala hampir sekuat neon — cacat yang tidak terlihat mata di
# kartu jadi, tapi membuat wajah berkabut. Neon dan grafiti senjata
# berkejenuhan ~195, jadi 95 memisahkan keduanya dengan lega.
BLOOM_RADIUS = 55
BLOOM_KUAT = 1.35
# Pinggiran kanvas bloom, supaya cahaya punya ruang meredup sampai NOL sebelum
# tepi persegi. Tanpa ini muncul cacat yang terlihat jelas di kartu jadi:
# senjata karakter menyentuh tepi kotak-batasnya, blur memotong cahayanya
# mendadak di situ, dan karena ImageChops.screen mengangkat latar DI DALAM
# persegi saja, batas perseginya terbaca sebagai kotak samar mengelilingi
# karakter. Diukur 9 Agu pada karakter tengah 777: 1392 piksel di tepi 1px
# bernilai > 0, satu sudut mencapai (13, 16, 12).
BLOOM_TEPI = BLOOM_RADIUS * 2

# Rim light: cahaya tepi di BELAKANG siluet, meniru sumber cahaya dari latar.
# Ia yang membuat karakter terlihat benar-benar berdiri di depan kebakaran,
# bukan ditumpuk di atasnya. Warnanya hangat mengikuti api di latar.
RIM_WARNA = (255, 150, 70)
RIM_TEBAL = 14
RIM_KUAT = 1.0

UPSCALE_DIR = Path(__file__).parent / 'upscaler'
UPSCALE_URL = ('https://github.com/xinntao/Real-ESRGAN/releases/download/'
               'v0.2.5.0/realesrgan-ncnn-vulkan-20220424-macos.zip')
UPSCALE_SHA256 = 'e0ad05580abfeb25f8d8fb55aaf7bedf552c375b5b4d9bd3c8d59764d2cc333a'
UPSCALE_MODEL = 'realesrgan-x4plus-anime'   # nama untuk bendera -n
UPSCALE_SKALA = 4
# realesr-animevideov3 dipakai lebih dulu karena ia paling menjaga tekstur
# kain. Ternyata itu ukuran yang salah: sebagian "tekstur" yang dijaganya
# adalah derau JPEG, dan pemilik menginginkan rupa yang halus dan melukis —
# yang terbaca mewah, bukan yang terbaca berbutir. Diadu ulang 9 Agu pada
# ekspor 2160 (perbandingan sebelumnya dibuat di 1080, waktu ketiganya
# sama-sama tergencet): x4plus-anime menang telak di wajah dan kain, dan
# TIDAK kalah di ukiran senjata — apinya justru lebih bersih dan motif
# bandana di celana lebih tegas. Ongkosnya 1,3 detik per karakter, dari 0,37.
#
# Nama BERKAS model tidak selalu sama dengan nama modelnya: rilis ini memberi
# akhiran -x4 pada realesr-animevideov3 tapi TIDAK pada realesrgan-x4plus-anime.
# Jadi ditulis apa adanya, bukan diturunkan dari rumus yang akan meleset diam-diam
# begitu modelnya diganti.
UPSCALE_BERKAS = 'realesrgan-x4plus-anime'
# Hanya tiga dari enam belas anggota arsip yang dipakai. Sembilan model lain
# tidak diekstrak: berkas yang tidak pernah dibuka.
_ANGGOTA = ('realesrgan-ncnn-vulkan',
            f'models/{UPSCALE_BERKAS}.bin',
            f'models/{UPSCALE_BERKAS}.param')


def _periksa_sidik(arsip: Path) -> None:
    """Bandingkan sha256 arsip dengan yang dipatok. Melempar kalau berbeda.

    Mesin akan MENJALANKAN isi arsip ini, jadi berkas yang tidak dikenal tidak
    boleh pernah diekstrak, apalagi dieksekusi.

    GalatFatal, bukan RuntimeError: sidik jari yang tidak cocok adalah isyarat
    rantai pasok — berkas yang akan DIEKSEKUSI mesin ini bukan berkas yang
    dipatok. Kalau ia menembus sebagai galat biasa, rakit.jalankan menangkapnya
    per akun dan melaporkannya sebagai "DILEWATI: gagal saat merakit" dengan
    exit 0, seolah masalahnya isi folder akun itu. Itu salah lapor terburuk
    yang bisa dihasilkan perkakas ini.
    """
    sidik = hashlib.sha256(arsip.read_bytes()).hexdigest()
    if sidik != UPSCALE_SHA256:
        raise antrean.GalatFatal(
            f'sidik jari arsip upscaler tidak cocok.\n'
            f'  diharapkan: {UPSCALE_SHA256}\n'
            f'  didapat   : {sidik}\n'
            f'Berkasnya tidak dijalankan dan tidak diekstrak.')


_PENANDA_SIAP = '.siap'
# Ekstraksi menulis ANGGOTA langsung ke path final (bukan temp-lalu-rename),
# jadi sebuah lari yang terputus di tengah bisa meninggalkan biner + sebagian
# model di disk. Kalau cache-hit memeriksa keberadaan berkas itu sendiri, lari
# berikutnya akan memperlakukan folder setengah jadi itu sebagai siap
# selamanya — tanpa .param, tanpa chmod, tanpa karantina dilepas, diam-diam.
# Penanda ini sengaja ditulis PALING AKHIR, sesudah ketiga anggota lengkap
# DAN chmod/xattr selesai, supaya keberadaannya sendiri adalah bukti bahwa
# seluruh urutan sebelumnya sukses — bukan cuma sebagian.


def _ambil_upscaler():
    """Kembalikan (biner, folder_model), mengunduh sekali kalau belum ada."""
    biner = UPSCALE_DIR / 'realesrgan-ncnn-vulkan'
    model = UPSCALE_DIR / 'models'
    penanda = UPSCALE_DIR / _PENANDA_SIAP
    if penanda.exists():
        return biner, model

    # Unduhan 52MB tidak boleh berlangsung tanpa suara: jalankan.command
    # diklik dua kali, dan layar diam adalah tanda macet, bukan tanda bekerja.
    print(f'  mengambil upscaler sekali saja (± 52 MB) dari {UPSCALE_URL}')
    UPSCALE_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as t:
        arsip = Path(t) / 'upscaler.zip'
        try:
            with urllib.request.urlopen(UPSCALE_URL, timeout=120) as sumber, \
                    open(arsip, 'wb') as tujuan:
                shutil.copyfileobj(sumber, tujuan)
        except (urllib.error.URLError, OSError) as e:
            # GalatFatal, sama alasannya dengan preflight biner potong di
            # rakit.jalankan: jaringan mati bukan cacat SATU folder akun. Kalau
            # ia lolos sebagai galat biasa, lari 30 akun tanpa pengawas keluar 0
            # dengan 30 baris DILEWATI yang identik — tak terbedakan dari 30
            # folder yang memang rusak sendiri-sendiri.
            raise antrean.GalatFatal(
                f'unduhan upscaler gagal: {e}. Perkakas ini butuh jaringan '
                f'sekali saja untuk mengambil {UPSCALE_URL}') from e

        _periksa_sidik(arsip)

        with zipfile.ZipFile(arsip) as z:
            for nama in _ANGGOTA:
                keluar = UPSCALE_DIR / nama
                keluar.parent.mkdir(parents=True, exist_ok=True)
                with z.open(nama) as isi, open(keluar, 'wb') as tulis:
                    shutil.copyfileobj(isi, tulis)

    biner.chmod(0o755)
    # Tanpa ini macOS menolak menjalankan berkas yang baru diunduh.
    #
    # Balikannya WAJIB diperiksa sebelum penanda ditulis. Kalau tidak,
    # karantina tetap menempel, "upscaler siap" tetap tercetak, dan .siap
    # menyatakan SELAMANYA bahwa folder ini beres — padahal binernya justru
    # yang ditolak macOS. Lari-lari berikutnya lalu pulang lewat cabang
    # cache-hit, gagal per akun dengan pesan buram dari biner yang tidak mau
    # jalan, dan tidak pernah mencoba melepas karantinanya lagi.
    lepas = subprocess.run(['xattr', '-dr', 'com.apple.quarantine', str(UPSCALE_DIR)],
                           capture_output=True, text=True)
    if lepas.returncode != 0:
        sebab = lepas.stderr.strip() or f'xattr keluar dengan kode {lepas.returncode}'
        raise antrean.GalatFatal(
            f'gagal melepas karantina macOS dari {UPSCALE_DIR}: {sebab}.\n'
            f'Penanda {_PENANDA_SIAP} sengaja TIDAK ditulis, jadi lari berikutnya '
            f'mengulang dari awal alih-alih memakai folder yang binernya ditolak '
            f'macOS. Kalau tetap gagal, jalankan sendiri:\n'
            f'  xattr -dr com.apple.quarantine {UPSCALE_DIR}\n'
            f'atau hapus folder itu lalu jalankan perakit ulang.')
    penanda.write_text('siap\n')
    print('  upscaler siap')
    return biner, model


def _naikkan_resolusi(im: Image.Image, tinggi_tayang: int) -> Image.Image:
    """Naikkan kutout 4x dengan Real-ESRGAN, kecuali ia sudah cukup besar.

    Dua alasan, dan yang kedua tidak kentara. Pertama, ia membalik arah rantai
    skala: kutout 226x570 yang tadinya DIBESARKAN 2,65x menjadi 1513px kini
    justru DIKECILKAN dari 2280px, dan mengecilkan selalu lebih bersih.
    Kedua, ia membuang derau yang membatasi structure dan sharpen — tanpa
    upscale, angka rasa yang sama membuat sweter hitam berbintik.

    Dilewati kalau kutoutnya sudah setinggi tayang: menaikkan 4x hanya untuk
    menurunkannya lagi memakan detik dan ratusan megabita tanpa hasil.
    """
    kotak = im.getchannel('A').getbbox()
    if kotak is not None and (kotak[3] - kotak[1]) >= tinggi_tayang:
        return im

    biner, model = _ambil_upscaler()
    with tempfile.TemporaryDirectory() as t:
        masuk, keluar = Path(t) / 'masuk.png', Path(t) / 'keluar.png'
        im.save(masuk)
        jalan = subprocess.run(
            [str(biner), '-i', str(masuk), '-o', str(keluar),
             '-s', str(UPSCALE_SKALA), '-n', UPSCALE_MODEL,
             '-m', str(model), '-f', 'png'],
            capture_output=True, text=True)
        if jalan.returncode != 0:
            raise RuntimeError(jalan.stderr.strip() or 'upscaler gagal tanpa pesan')
        return Image.open(keluar).convert('RGBA')


def _kikis_pinggiran(im: Image.Image) -> Image.Image:
    """Kikis kanal alfa beberapa piksel ke dalam supaya serambut warna latar ikut terbuang."""
    alfa = im.getchannel('A')
    for _ in range(KIKIS_PIKSEL):
        alfa = alfa.filter(ImageFilter.MinFilter(3))
    im = im.copy()
    im.putalpha(alfa)
    return im


def _perlakukan_latar(im: Image.Image) -> Image.Image:
    """Blur lalu redupkan latar supaya ia berhenti bersaing dengan karakter."""
    kabur = im.filter(ImageFilter.GaussianBlur(LATAR_BLUR))
    redup = ImageEnhance.Brightness(kabur.convert('RGB')).enhance(LATAR_REDUP)
    return redup.convert('RGBA')


def _perlakukan_karakter(im: Image.Image) -> Image.Image:
    """Angkat tekstur, tepi, kontras, dan warna kutout. Alfa disalin utuh.

    Alfa sengaja dipisah dan dikembalikan apa adanya: kalau ia ikut
    dipertajam, tepinya melahirkan halo.
    """
    alfa = im.getchannel('A')
    rgb = im.convert('RGB')
    rgb = rgb.filter(ImageFilter.UnsharpMask(STRUKTUR[0], STRUKTUR[1], 0))
    rgb = rgb.filter(ImageFilter.UnsharpMask(*UNSHARP))
    rgb = ImageEnhance.Contrast(rgb).enhance(KONTRAS)
    rgb = ImageEnhance.Color(rgb).enhance(SATURASI)
    hasil = rgb.convert('RGBA')
    hasil.putalpha(alfa)
    return hasil


def _bloom(im: Image.Image) -> Image.Image:
    """Cahaya yang keluar dari benda terang DAN berwarna pekat. RGB, untuk dilayar-kan.

    Dua syarat, bukan satu. Terang saja akan membuat kulit, kaus putih, dan
    kain abu ikut berkabut — kartunya jadi terlihat berembun, bukan mewah.
    Kejenuhan warna yang membedakan api, neon, dan grafiti senjata dari
    permukaan pucat yang kebetulan terkena cahaya.
    """
    rgb = im.convert('RGB')
    r, g, b = rgb.split()
    terang = rgb.convert('L')
    # Kejenuhan kasar tanpa konversi HSV: selisih kanal terkuat dan terlemah.
    jenuh = ImageChops.subtract(ImageChops.lighter(ImageChops.lighter(r, g), b),
                                ImageChops.darker(ImageChops.darker(r, g), b))

    pilih = ImageChops.multiply(
        terang.point(lambda v: 255 if v > BLOOM_AMBANG else 0),
        jenuh.point(lambda v: 255 if v > BLOOM_JENUH else 0))
    # Dibatasi siluet: cahaya hanya boleh lahir dari karakternya sendiri.
    pilih = ImageChops.multiply(pilih, im.getchannel('A'))

    # Kanvas dilebihkan BLOOM_TEPI di keempat sisi supaya cahaya meredup
    # sampai nol di dalam gambar, bukan terpotong di tepinya. Pemanggil
    # menempelnya balik pada (x - BLOOM_TEPI, y - BLOOM_TEPI).
    sumber = Image.new('RGB', (rgb.width + 2 * BLOOM_TEPI,
                               rgb.height + 2 * BLOOM_TEPI), (0, 0, 0))
    sumber.paste(rgb, (BLOOM_TEPI, BLOOM_TEPI), pilih)
    kabur = sumber.filter(ImageFilter.GaussianBlur(BLOOM_RADIUS))
    kabur = ImageEnhance.Brightness(kabur).enhance(BLOOM_KUAT)
    # Sisa haze numerik beberapa aras tetap cukup untuk terbaca sebagai kotak
    # begitu dilayar-kan. Dipotong habis, lalu direntangkan kembali supaya
    # cahaya yang sungguhan tidak ikut meredup.
    return kabur.point(lambda v: max(0, (v - 8) * 255 // 247))


def _rim_light(im: Image.Image) -> Image.Image:
    """Cincin cahaya di LUAR siluet, untuk ditempel di belakang karakter.

    Bagian dalam siluet sengaja dikurangkan habis: rim light yang bocor ke
    dalam badan berhenti terbaca sebagai cahaya tepi dan mulai terbaca
    sebagai kabut.
    """
    alfa = im.getchannel('A')
    lebar = alfa
    for _ in range(RIM_TEBAL):
        lebar = lebar.filter(ImageFilter.MaxFilter(3))
    cincin = ImageChops.subtract(lebar, alfa)
    cincin = cincin.filter(ImageFilter.GaussianBlur(RIM_TEBAL * 0.9))
    # Blur mengembalikan sedikit cahaya ke dalam siluet; dipotong lagi supaya
    # janji "hanya di luar" benar-benar dipegang, bukan hampir dipegang.
    cincin = ImageChops.subtract(cincin, alfa)
    if RIM_KUAT != 1.0:
        cincin = cincin.point(lambda v: min(255, int(v * RIM_KUAT)))
    lapis = Image.new('RGBA', im.size, RIM_WARNA + (0,))
    lapis.putalpha(cincin)
    return lapis


# Label template ditulis putih. Di atas 165 aras rata-rata, teks putih mulai
# hilang ke latarnya. Diukur pada kasus nyata yang memicu cek ini: sepatu
# merah-putih 777 di belakang kata 'Detail'.
AMBANG_LATAR_LABEL = 165


def _latar_label_terlalu_terang(petak: Image.Image) -> bool:
    """Benarkah petak ini terlalu terang untuk menampung teks putih di atasnya?

    Label TIDAK PERNAH tertutup karakter — bingkai template di-composite paling
    akhir, jadi tulisannya selalu tergambar. Yang bisa rusak adalah kontrasnya.
    Maka yang diukur kecerahan, bukan tumpang tindih siluet.
    """
    titik = list(petak.convert('L').getdata())
    return sum(titik) / len(titik) > AMBANG_LATAR_LABEL


def _potong(berkas: Path, tujuan: Path) -> Image.Image:
    if not POTONG.exists():
        raise FileNotFoundError(
            f'biner pemotong belum dikompilasi: {POTONG}. '
            f'Jalankan: swiftc -O -o {POTONG} {POTONG}.swift')
    jalan = subprocess.run([str(POTONG), str(berkas), str(tujuan)],
                           capture_output=True, text=True)
    if jalan.returncode != 0:
        raise RuntimeError(jalan.stderr.strip() or f'pemotong gagal pada {berkas.name}')
    return _kikis_pinggiran(Image.open(tujuan).convert('RGBA'))


def inti_alfa(im: Image.Image) -> Tuple[int, int]:
    """Rentang kolom (kiri, kanan) yang memuat BADAN karakter, bukan jubahnya.

    Kotak-batas alfa memberi lebar TERLUAR: jubah yang mengembang, aura, dan
    senjata yang menjulur mendatar semuanya ikut. Untuk memutuskan seberapa
    besar karakter boleh digambar, yang relevan bukan itu melainkan lebar
    badannya — jubah bisa menyelinap di belakang tetangganya tanpa membuat
    keduanya terbaca sebagai satu gumpalan.

    Ukurannya cakupan tegak per kolom; lihat INTI_CAKUPAN untuk angkanya dan
    bahan yang memunculkannya. Balikannya sebidang dengan kotak-batas alfa:
    koordinat kolom pada gambar yang diberikan, kanan bersifat eksklusif.

    Kutout yang seluruhnya tipis — tak satu kolom pun mencapai ambang — jatuh
    kembali ke kotak-batas alfa. Tanpa itu ia akan berlebar nol dan
    dibesarkan tanpa batas oleh pemanggilnya.
    """
    alfa = im.getchannel('A')
    lebar = alfa.width
    # BOX = rerata tiap kolom. Dipakai alih-alih menghitung piksel satu per
    # satu karena ia berjalan di C: kutout produksi keluar 4x dari upscaler,
    # dan menyapu 2280 x 904 piksel dari Python terasa di setiap lari.
    pekat = alfa.point(lambda v: 255 if v >= INTI_PEKAT else 0)
    kolom = pekat.resize((lebar, 1), Image.Resampling.BOX).getdata()

    isi = [x for x, v in enumerate(kolom) if v >= INTI_CAKUPAN * 255]
    if not isi:
        kotak = alfa.getbbox()
        return (0, lebar) if kotak is None else (kotak[0], kotak[2])
    return isi[0], isi[-1] + 1


def tata_letak(kanvas: Tuple[int, int],
               kotak_alfa: List[Tuple[int, int, int, int]],
               inti: Optional[List[Tuple[int, int]]] = None,
               ) -> List[Tuple[int, int, int, int]]:
    """Hitung posisi tiga karakter: tinggi setara, kaki menapak satu garis.

    Dinormalkan lewat kotak-batas ALFA, bukan ukuran berkas. Potongan datang
    beragam — 605px dan 1001px pada contoh nyata — dan ukuran berkas ikut
    memuat ruang kosong di sekitar karakter, jadi menskala dengannya membuat
    karakter yang potongannya longgar terlihat kerdil.

    `inti` memberi rentang kolom badan tiap karakter (lihat inti_alfa),
    sebidang dengan kotak_alfa. Ia yang dipakai untuk membagi lebar panggung
    dan menjamin celah; kotak_alfa tetap yang menentukan tinggi dan ukuran
    tempel. Kalau tidak diberikan, inti disamakan dengan kotak-batas — perilaku
    lama, dan itulah yang dipakai cek-cek yang memang mengukur kotak-batas.
    """
    if len(kotak_alfa) != 3:
        raise ValueError(f'poster butuh tepat 3 karakter, diberi {len(kotak_alfa)}')
    if inti is None:
        inti = [(kiri, kanan) for kiri, _, kanan, _ in kotak_alfa]
    if len(inti) != 3:
        raise ValueError(f'inti butuh tepat 3 rentang, diberi {len(inti)}')

    lebar_kanvas, tinggi_kanvas = kanvas
    dasar = round(tinggi_kanvas * GARIS_DASAR)

    faktor = []
    lebar_pakai = []
    for i, (kiri, _, kanan, bawah) in enumerate(kotak_alfa):
        tinggi_alfa = bawah - kotak_alfa[i][1]
        target = tinggi_kanvas * TINGGI_KARAKTER * (SKALA_TENGAH if i == 1 else 1.0)
        f = target / tinggi_alfa
        faktor.append(f)
        lebar_pakai.append((inti[i][1] - inti[i][0]) * f)

    # Poster rujukan pemilik punya celah latar yang TERLIHAT di antara ketiga
    # karakter, dan itu sebagian besar yang membuatnya terbaca rapi. Punya kami
    # tidak punya celah itu — bukan karena posisinya salah (diukur, pusatnya
    # sudah sama) melainkan karena LEBARNYA. Pose menentukan lebar, dan pose
    # berbeda tiap akun: pada 777 senjata naga karakter kanan menjulur mendatar
    # 1071px, sehingga ketiganya butuh 2598px di panggung 2353px — kelebihan
    # 245px sebelum celah apa pun.
    #
    # Maka ukurannya diturunkan SEPERLUNYA, per akun, bukan dipatok satu angka
    # global yang harus muat untuk kasus terburuk. Akun berpose rapat tetap
    # besar; yang menjulur mengalah sedikit. Ini yang membuat celah muncul
    # tanpa mengorbankan akun lain.
    celah = round(lebar_kanvas * CELAH_MINIMUM)
    muat = lebar_kanvas - 2 * celah
    if sum(lebar_pakai) > muat:
        susut = muat / sum(lebar_pakai)
        faktor = [f * susut for f in faktor]

    ukuran = [(max(1, round((kanan - kiri) * faktor[i])),
               max(1, round((bawah - atas) * faktor[i])))
              for i, (kiri, atas, kanan, bawah) in enumerate(kotak_alfa)]
    ukuran_inti = [max(1, round((inti[i][1] - inti[i][0]) * faktor[i]))
                   for i in range(3)]

    # Celahnya DIBAGIKAN, bukan diharapkan muncul. POS_X dulu memaku pusat tiap
    # karakter di 0,23/0,50/0,77 tanpa peduli lebarnya — jadi menyusutkan lebar
    # tidak melahirkan celah sama sekali, karena jarak antar pusat tetap. Pada
    # 777 itu menyisakan celah -137px: badan yang bertumpuk, persis yang
    # ditolak pemilik.
    #
    # Sekarang ketiganya ditata bersambung dengan celah yang sama besar lalu
    # digeser supaya kelompoknya berada di tengah. Untuk pose simetris hasilnya
    # praktis sama dengan 0,23/0,50/0,77 yang lama; bedanya baru terasa ketika
    # satu karakter jauh lebih lebar, dan di situlah yang lama gagal.
    #
    # Yang ditata BADANnya, dan yang dikembalikan kotak TEMPELnya. Keduanya
    # tidak sama begitu ada jubah: badan diletakkan di slotnya, lalu titik
    # tempel digeser ke kiri sejauh jarak jubah dari tepi kotak-batas — jadi
    # jubahnya menggantung keluar slot, bukan mendorong badan menjauh.
    total = sum(ukuran_inti)
    sisa = lebar_kanvas - total
    celah_nyata = min(celah, sisa // 2) if sisa > 0 else 0
    x = (lebar_kanvas - (total + 2 * celah_nyata)) // 2

    tempat = []
    for i, (lebar, tinggi) in enumerate(ukuran):
        geser = round((inti[i][0] - kotak_alfa[i][0]) * faktor[i])
        tempat.append((x - geser, dasar - tinggi, lebar, tinggi))
        x += ukuran_inti[i] + celah_nyata

    return tempat


def inti_tayang(tempat: List[Tuple[int, int, int, int]],
                kotak_alfa: List[Tuple[int, int, int, int]],
                inti: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """(x, lebar) badan tiap karakter pada kanvas, sejalan dengan tata_letak.

    Dipakai untuk apa pun yang harus menempel pada BADAN alih-alih pada
    kotak-batas — bayangan kaki yang pertama. Diturunkan dari balikan
    tata_letak, bukan dihitung ulang dari konstanta, supaya ia tidak bisa
    berselisih diam-diam kalau tata letaknya disetel.
    """
    hasil = []
    for (x, _, lebar, _), (kiri, _, kanan, _), (inti_kiri, inti_kanan) in zip(
            tempat, kotak_alfa, inti):
        skala = lebar / (kanan - kiri)
        hasil.append((x + round((inti_kiri - kiri) * skala),
                      max(1, round((inti_kanan - inti_kiri) * skala))))
    return hasil


def rakit(akun, aset: Path, catat: Optional[List[str]] = None) -> Image.Image:
    """Rakit poster: tiga karakter asli di atas latar sesuai tingkat.

    `catat`, kalau diberikan, menerima satu baris per karakter yang lebarnya
    melebihi panggung setelah dinormalkan — potongan Vision membawa massa
    tersambung, jadi peliharaan yang menempel senjata atau senjata yang
    dipegang mendatar bisa melebarkan kotak-batas sampai tepi kanvas
    memotongnya. `Image.paste` memotong itu tanpa protes; kartunya tetap
    dirakit (pemilik yang berhak memutuskan), tapi pemanggil harus tahu.
    """
    aset = Path(aset)
    # Latar tinggal di LUAR mesin/, di latar/ — ia aset yang memang
    # diganti-ganti pemilik, bukan bagian mesin yang tidak disentuh. Dibaca lewat
    # konstanta modul, bukan parameter, supaya jalur produksi cuma satu.
    berkas_latar = LATAR_BAWAAN / f'{akun.tingkat}.png'
    if not berkas_latar.is_file():
        raise FileNotFoundError(
            f'latar untuk tingkat "{akun.tingkat}" tidak ada: {berkas_latar}')

    # Perlakuan latar HARUS sebelum bayangan kaki digambar. Kalau sesudah,
    # bayangannya ikut terblur dua kali dan kaki kehilangan pijakan.
    latar = _perlakukan_latar(Image.open(berkas_latar).convert('RGBA'))

    with tempfile.TemporaryDirectory() as t:
        # Tinggi tayang terbesar (karakter tengah) jadi patokan pelewatan.
        # Diturunkan dari konstanta tata letak, bukan ditulis ulang sebagai
        # angka kedua yang bisa berselisih diam-diam kalau tata letaknya disetel.
        tinggi_tayang = round(latar.height * TINGGI_KARAKTER * SKALA_TENGAH)
        # Upscale SESUDAH _kikis_pinggiran: KIKIS_PIKSEL dikalibrasi pada skala
        # sumber dan akan salah takaran pada gambar yang sudah membesar 4x.
        potongan = [_naikkan_resolusi(_potong(b, Path(t) / f'{i}.png'), tinggi_tayang)
                    for i, b in enumerate(akun.karakter)]

        kotak_alfa = []
        for p in potongan:
            kotak = p.getchannel('A').getbbox()
            if kotak is None:
                raise RuntimeError(
                    'hasil potong kosong — dua kemungkinan: Vision tidak menemukan subjek '
                    'sama sekali, atau erosi _kikis_pinggiran menghabiskan siluet tipis '
                    'sampai tak tersisa piksel alfa')
            kotak_alfa.append(kotak)

        inti = [inti_alfa(p) for p in potongan]
        tempat = tata_letak(latar.size, kotak_alfa, inti)

        if catat is not None:
            # Peringatan lama berbunyi "karakter N terpotong tepi poster". Ia
            # kini tidak bisa menyala lagi: tata_letak menyusutkan ketiganya
            # sampai muat berikut celah, jadi tidak ada yang bisa terpotong.
            # Yang MASIH perlu diketahui pemilik adalah harganya — kartu yang
            # tampak lebih kecil dari biasanya bukan kebetulan, melainkan
            # akibat satu pose yang menjulur lebar.
            target = latar.height * TINGGI_KARAKTER * SKALA_TENGAH
            nyata = tempat[1][3]
            if nyata < target * 0.97:
                catat.append(
                    f'karakter diperkecil {(1 - nyata / target) * 100:.0f}% supaya '
                    f'ketiganya muat berikut celah — biasanya karena satu pose '
                    f'menjulurkan senjata mendatar')

        # Bayangan dulu untuk SEMUA karakter, baru karakternya. Kalau bayangan
        # digambar per karakter, bayangan yang tengah akan menimpa kaki
        # karakter samping yang sudah tertempel.
        #
        # Diukur dari BADAN, bukan kotak-batas: pada kutout berjubah, pusat
        # kotak-batas duduk jauh di dalam jubah, dan bayangan yang mengikutinya
        # terbaca sebagai genangan yang tidak menyentuh kaki siapa pun.
        bayangan = Image.new('RGBA', latar.size, (0, 0, 0, 0))
        pena = ImageDraw.Draw(bayangan)
        for (_, y, _, tinggi), (xi, lebar_inti) in zip(
                tempat, inti_tayang(tempat, kotak_alfa, inti)):
            rx, ry = lebar_inti * 0.42, tinggi * 0.045
            cx, cy = xi + lebar_inti / 2, y + tinggi
            pena.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=WARNA_BAYANGAN)
        latar = Image.alpha_composite(latar, bayangan.filter(ImageFilter.GaussianBlur(18)))

        # Tengah DULU, sisi di atasnya. Kebalikan dari yang berlaku sampai
        # 14 Agu ("tengah paling akhir supaya tumpang tindih di depan").
        #
        # Alasannya berubah begitu lebar diukur dari inti badan: yang bisa
        # bertumpuk sekarang cuma yang MENJULUR — jubah, ujung senjata,
        # peliharaan yang menempel — karena badan dijamin punya celah. Dan
        # untuk juluran, "di depan" justru yang salah: peliharaan
        # FF-REGULER-6001 menutupi badan bawah karakter kanan dan kartunya
        # terbaca berantakan. Di belakang, ia mengintip dari balik tetangganya
        # dan terbaca sebagai kedalaman.
        #
        # Yang tengah tetap yang terbesar dan tetap jadi titik pandang; itu
        # datang dari SKALA_TENGAH, bukan dari urutan tempel.
        for i in (1, 0, 2):
            x, y, lebar, tinggi = tempat[i]
            # Diperlakukan SETELAH diskalakan ke ukuran tayang. Mempertajam
            # sebelum resize sia-sia: resampling membubarkan lagi hasilnya.
            p = potongan[i].crop(kotak_alfa[i]).resize(
                (lebar, tinggi), Image.Resampling.LANCZOS)
            p = _perlakukan_karakter(p)

            # Urutan tiga langkah ini mengikat. Rim light DI BELAKANG karakter
            # supaya ia terbaca sebagai cahaya latar yang menyapu tepi, bukan
            # garis yang digambar di atas badan. Bloom SESUDAH karakter
            # tertempel, dilayar-kan ke seluruh kanvas, supaya cahayanya jatuh
            # ke latar di sekitarnya — cahaya yang berhenti di tepi siluet
            # tidak terbaca sebagai cahaya.
            cincin = _rim_light(p)
            lapis = Image.new('RGBA', latar.size, (0, 0, 0, 0))
            lapis.paste(cincin, (x, y), cincin)
            latar = Image.alpha_composite(latar, lapis)

            latar.paste(p, (x, y), p)

            cahaya = Image.new('RGB', latar.size, (0, 0, 0))
            cahaya.paste(_bloom(p), (x - BLOOM_TEPI, y - BLOOM_TEPI))
            latar = ImageChops.screen(latar.convert('RGB'), cahaya).convert('RGBA')

    rona = Image.new('RGBA', latar.size, RONA_HANGAT)
    return Image.alpha_composite(latar, rona)
