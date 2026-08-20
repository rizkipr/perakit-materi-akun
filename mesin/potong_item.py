#!/usr/bin/env python3
"""Potong petak ikon item dari screenshot layar Fashion Free Fire.

Pakai:
    python3 mesin/potong_item.py <screenshot> <folder-tujuan> [nomor ...]

Tanpa nomor, seluruh petak yang utuh dipotong dan diberi nama urut. Dengan
nomor, hanya petak itu yang diambil dan dinamai 1..4 sesuai urutan yang kamu
sebut — jadi `... 3 1 6 2` menaruh petak 3 di slot pertama kartu.

POSISI STRIP DICARI SENDIRI, TIDAK DIPAKU. Versi pertama memaku koordinat dari
satu screenshot dan langsung meleset pada screenshot berikutnya. Tiga hal
menggesernya tanpa mengubah bentuknya: lebar teks UI berbeda antar bahasa
(layar "ALL RARITY" tidak sama dengan "SEMUA TIER"), daftarnya bisa tergulir,
dan WhatsApp mengecilkan gambar dengan skala x dan y yang sedikit berbeda.

Yang TIDAK dicari adalah jaraknya. 155/1320 tinggi gambar terbukti sama persis
pada screenshot 2868x1320 asli maupun 1600x739 hasil kompresi WhatsApp, jadi
menebaknya lagi tiap kali cuma menambah cara untuk gagal. Yang dicari cuma
pergeserannya: di kolom mana angka rata kanan, dan di baris mana alas angka.

Caranya mencocokkan pola berkala — angka muncul tiap satu jarak, jadi fase yang
benar adalah yang membuat paling banyak kotak angka berisi piksel terang.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image

# Jarak antar petak, pecahan tinggi gambar. Cocok di dua resolusi yang jauh beda.
JARAK = 155 / 1320

# Ukuran petak dan jarak tepinya, relatif terhadap JARAK — bukan terhadap tinggi
# gambar — supaya semuanya ikut kalau jaraknya suatu saat berubah.
# Tinggi dinaikkan dari 127/155 setelah pemilik menunjuk ikon celana terpotong
# pinggangnya: ikon terjangkung di strip menjulang lebih tinggi daripada ikon
# kepala atau masker. Lebarnya ikut supaya rasio tetap ~ slot template (0,991);
# kalau tidak, skala_menutup membuang selisihnya dari sisi terpanjang.
# 0,945 -> kotak menjangkau 0,868 jarak di atas alas angka, praktis seluruh
# tinggi satu petak (batas petaknya sendiri ~0,87). Diukur: ikon terjangkung di
# strip pemilik mencapai 0,83 jarak, jadi masih bersisa. Nilai lama 127/155
# cuma menjangkau 0,74 dan memenggal pinggang ikon celana.
TINGGI_PETAK = 0.945
LEBAR_PETAK = TINGGI_PETAK * (324 / 327)
KANAN_DARI_ANGKA = 9 / 155     # napas di kanan angka
BAWAH_DARI_ANGKA = 12 / 155    # napas di bawah angka; tanpa ini angkanya
                               # menyentuh lengkung sudut slot dan terbaca terpotong

# Wilayah pencarian strip, pecahan lebar gambar: selalu di kiri, antara menu
# kategori dan kisi item.
CARI_X0, CARI_X1 = 0.06, 0.32

# Berapa petak harus cocok sebelum sebuah fase dipercaya. Diukur pada 17
# screenshot pemilik (7 layar Armory, 10 layar Fashion): di ambang 4, empat layar
# Armory ikut lolos dengan mencocokkan daftar senjatanya — potongan sampah yang
# tidak kelihatan salah. Ambang 5-7 memisahkan keduanya sempurna; dipilih 6
# supaya ada margin ke dua arah.
MINIMAL_PETAK_COCOK = 6

BATAS_PETAK = 40   # penjaga putaran, jauh di atas jumlah petak yang mungkin


class GagalKalibrasi(Exception):
    """Strip ikon tidak ketemu di gambar ini.

    Kelasnya sendiri supaya pemanggil bisa membedakan "ini bukan layar Fashion"
    dari galat baca berkas biasa.
    """


def kalibrasi(im: Image.Image) -> Tuple[int, float, float]:
    """Cari (kanan_angka, alas_angka_pertama, jarak) pada sebuah layar Fashion.

    `alas_angka_pertama` boleh jatuh di atas tepi gambar — ia fase pola, bukan
    janji bahwa petak pertama kelihatan utuh. `nomor_pertama_utuh` yang memutuskan
    petak mana yang layak dipotong.
    """
    lebar, tinggi = im.size
    jarak = JARAK * tinggi

    x0, x1 = int(lebar * CARI_X0), int(lebar * CARI_X1)
    wilayah = im.convert('L').crop((x0, 0, x1, tinggi))

    # Ambang adaptif: angka jauh lebih terang daripada apa pun di strip, tapi
    # nilai mutlaknya turun karena kompresi JPEG melunakkan putihnya.
    hist = wilayah.histogram()
    total = sum(hist)
    kum, ambang = 0, 200
    for v in range(255, -1, -1):
        kum += hist[v]
        if kum >= total * 0.010:
            ambang = max(v, 170)
            break

    biner = wilayah.point(lambda v: 255 if v >= ambang else 0)
    w, h = biner.size
    data = biner.tobytes()

    lebar_angka = max(6, int(jarak * 0.62))
    tinggi_angka = max(4, int(jarak * 0.17))

    def piksel_angka(kanan: int, alas: float) -> int:
        n = 0
        for y in range(max(0, int(alas - tinggi_angka)), min(h, int(alas))):
            baris = data[y * w:(y + 1) * w]
            n += baris.count(b'\xff', max(0, kanan - lebar_angka), max(0, kanan))
        return n

    terbaik = None
    langkah_x = max(1, int(lebar * 0.0015))
    langkah_fase = max(1, int(jarak * 0.02))
    for kanan in range(int(w * 0.20), w, langkah_x):
        for fase in range(0, int(jarak), langkah_fase):
            cocok = 0
            skor = 0.0
            n = 0
            while True:
                alas = fase + jarak * n
                if alas > h:
                    break
                c = piksel_angka(kanan, alas)
                if c >= tinggi_angka:
                    cocok += 1
                    # Skor TIDAK dibatasi. Dulu dibatasi, dan akibatnya begitu
                    # cukup piksel tertangkap semua kolom bernilai sama — yang
                    # menang jadi kolom paling kiri, belasan piksel dari
                    # seharusnya. Tanpa batas, cakupan penuh yang menang.
                    skor += c
                n += 1
            if cocok >= MINIMAL_PETAK_COCOK and (terbaik is None or (cocok, skor) > terbaik[0]):
                terbaik = ((cocok, skor), x0 + kanan, float(fase))

    if terbaik is None:
        raise GagalKalibrasi(
            'strip ikon tidak ketemu — pastikan ini screenshot layar Fashion '
            'yang memperlihatkan deretan ikon beserta angkanya di sisi kiri')

    kanan_terbaik, fase = terbaik[1], terbaik[2]
    # Dibinerkan ULANG dengan ambang lebih lunak khusus untuk penguncian.
    # Ambang keras dipakai pencarian fase supaya derau tidak ikut, tapi ia
    # memotong ekor anti-alias di bawah angka — dan ekor itulah yang mata
    # lihat sebagai dasar angka. Diukur 9 Agu pada FF-REGULER-6002: dasar
    # yang ditemukan ambang keras 3-4px di atas dasar yang terlihat, dan
    # angkanya tetap terpotong walau kalibrasinya "benar".
    lembut = wilayah.point(lambda v: 255 if v >= max(90, ambang * 0.62) else 0)
    alas = _perhalus_alas(lembut, x0, kanan_terbaik, fase, jarak)
    return (_perhalus_kanan(lembut, x0, kanan_terbaik, alas, jarak), alas, jarak)


def _perhalus_kanan(biner: Image.Image, x0: int, kanan: int,
                    alas: float, jarak: float) -> int:
    """Kunci kolom ke tepi kanan ANGKA, bukan ke skor pita.

    Cacat kembar dari _perhalus_alas, cuma di sumbu lain. Pencarian kolom
    memaksimalkan piksel terang, dan pada layar berbahasa Indonesia kisi item
    duduk rapat di sebelah kanan strip — kisi itu terang, jadi kolom yang
    sedikit ke kanan mencetak skor lebih tinggi. Diukur 9 Agu pada layar
    FF-REGULER-6001: kolom meleset 18-19px ke kanan, yaitu 23% lebar petak,
    dan tiap potongan memuat sepotong kisi di tepinya.

    Pembedanya sama: BENTUK. Angka itu gumpalan kolom terang yang RINGKAS,
    selebar ~0,3 jarak. Kisi item jauh lebih lebar. Jadi gumpalan dikumpulkan,
    yang terlalu lebar dibuang, lalu dipilih yang tepi kanannya paling dekat ke
    tebakan. Median antar petak, supaya satu petak aneh tidak menggeser strip.
    """
    w, h = biner.size
    data = biner.tobytes()
    tinggi_angka = max(3, int(jarak * 0.17))
    jendela = max(4, int(jarak * 0.30))
    lebar_maks = max(4, int(jarak * 0.55))

    def tepi_gumpalan(alas_petak: float):
        y0 = max(0, int(alas_petak - tinggi_angka))
        y1 = min(h, int(alas_petak))
        if y1 <= y0:
            return None
        # Dipindai lebih lebar daripada jendela pemilihan supaya lebar tiap
        # gumpalan terukur utuh — kalau terpotong jendela, kisi yang lebar
        # terbaca ringkas dan lolos saringan.
        kiri = max(0, kanan - x0 - int(jarak * 1.2))
        kanan_pindai = min(w, kanan - x0 + int(jarak * 0.8))
        terang = []
        for x in range(kiri, kanan_pindai):
            n = sum(1 for y in range(y0, y1) if data[y * w + x] == 255)
            terang.append(n >= 2)
        gumpal, mulai = [], None
        for i, ada in enumerate(terang):
            if ada and mulai is None:
                mulai = i
            elif not ada and mulai is not None:
                gumpal.append((kiri + mulai, kiri + i))
                mulai = None
        if mulai is not None:
            gumpal.append((kiri + mulai, kiri + len(terang)))
        calon = [b for a, b in gumpal
                 if b - a <= lebar_maks and abs(b - (kanan - x0)) <= jendela]
        if not calon:
            return None
        return min(calon, key=lambda b: abs(b - (kanan - x0)))

    geser = []
    n = 0
    while True:
        a = alas + jarak * n
        if a > h + jarak:
            break
        n += 1
        if a < tinggi_angka:
            continue
        b = tepi_gumpalan(a)
        if b is not None:
            geser.append(b - (kanan - x0))

    if not geser:
        return kanan
    geser.sort()
    return kanan + geser[len(geser) // 2]


def _perhalus_alas(biner: Image.Image, x0: int, kanan: int,
                   fase: float, jarak: float) -> float:
    """Kunci fase ke DASAR angka yang sebenarnya, bukan ke skor pita.

    Pencarian fase memaksimalkan piksel terang dalam pita setinggi 0,17 jarak.
    Pita itu selebar 0,62 jarak, dan di layar sungguhan dasar IKON juga terang —
    rambut putih, rompi, celana. Akibatnya fase yang sedikit naik bisa mencetak
    skor lebih tinggi daripada fase yang duduk pas di angka. Diukur 9 Agu pada
    IMG_5924.PNG: fase meleset 19px ke atas, dan keempat angka di kartu jadi
    terpenggal 6-7px.

    Menaikkan napas di bawah angka TIDAK menyelesaikannya — itu menambal satu
    screenshot dan menggeser masalahnya ke screenshot berikutnya. Yang benar
    adalah mengunci: setelah fase kasar ketemu, tiap petak diperiksa di jendela
    sempit dan dicari baris terang PALING BAWAH, yaitu dasar angka yang nyata.
    Yang dipakai MEDIANnya, bukan reratanya, supaya satu petak aneh — ikon yang
    menjulur ke bawah, atau angka yang tertutup badge "NEW" — tidak menggeser
    seluruh strip.
    """
    w, h = biner.size
    data = biner.tobytes()
    kanan_lokal = kanan - x0
    # Kolom sempit: angka rata kanan dan tidak selebar ikonnya.
    kiri_lokal = max(0, kanan_lokal - int(jarak * 0.45))

    # Yang membedakan angka dari ikon BUKAN jaraknya, melainkan BENTUKNYA.
    # Sempat dicoba jendela pencarian: longgar ke bawah mengunci ke dasar ikon
    # petak berikutnya, sempit ke bawah tidak sanggup menjangkau dasar angka
    # ketika tebakan awal meleset jauh ke atas. Menyetel angkanya jadi tarik-
    # menarik antara dua kegagalan — tanda pendekatannya yang keliru.
    #
    # Angka adalah pita terang RINGKAS, tinggi ~0,17 jarak. Ikon jauh lebih
    # tinggi. Jadi pita dikumpulkan dulu, yang terlalu tinggi dibuang, lalu
    # dipilih yang dasarnya PALING DEKAT ke tebakan.
    jendela = max(6, int(jarak * 0.30))
    tinggi_maks = max(4, int(jarak * 0.30))

    def dasar_pita(alas: float):
        # Dipindai LEBIH LEBAR daripada jendela pemilihan supaya tinggi tiap
        # pita terukur utuh. Kalau pemindaiannya sesempit jendela, pita ikon
        # setinggi 98px terpotong jadi 31px dan lolos saringan tinggi — cacat
        # yang ditangkap cek '_perhalus_alas' pada tebakan -19px.
        lo = max(0, int(alas - jarak * 0.80))
        hi = min(h, int(alas + jarak * 0.35))
        pita, mulai = [], None
        for y in range(lo, hi):
            terang = data[y * w + kiri_lokal:y * w + kanan_lokal].count(b'\xff') >= 3
            if terang and mulai is None:
                mulai = y
            elif not terang and mulai is not None:
                pita.append((mulai, y))
                mulai = None
        if mulai is not None:
            pita.append((mulai, hi))
        calon = [b for a, b in pita
                 if b - a <= tinggi_maks and abs(b - alas) <= jendela]
        if not calon:
            return None
        return min(calon, key=lambda b: abs(b - alas))

    geser = []
    n = 0
    while True:
        alas = fase + jarak * n
        if alas > h + jarak:
            break
        n += 1
        if alas < 0:
            continue
        b = dasar_pita(alas)
        if b is not None:
            geser.append(b - alas)

    if not geser:
        return fase
    geser.sort()
    return fase + geser[len(geser) // 2]



def kotak_petak(kal: Tuple[int, float, float], nomor: int):
    """Kotak (kiri, atas, kanan, bawah) petak ke-`nomor`, mulai dari 1."""
    if nomor < 1:
        raise ValueError(f'nomor petak mulai dari 1, diberi {nomor}')

    kanan_angka, alas_pertama, jarak = kal
    kanan = round(kanan_angka + jarak * KANAN_DARI_ANGKA)
    bawah = round(alas_pertama + jarak * (nomor - 1) + jarak * BAWAH_DARI_ANGKA)
    return (kanan - round(jarak * LEBAR_PETAK),
            bawah - round(jarak * TINGGI_PETAK),
            kanan, bawah)


# Bingkai seleksi UI Free Fire. Layar Fashion SELALU menandai satu slot yang
# sedang dilihat, jadi di screenshot mana pun ada tepat satu petak yang terlihat
# beda sendiri.
#
# Pendeteksinya BUTA WARNA, dan itu disengaja. Versi pertama cuma mengenal
# kuning, lalu FF-REGULER-6002 ternyata memakai bingkai BIRU — tema UI berbeda,
# dan menambah satu warna lagi cuma menunda kegagalan ke tema berikutnya.
# Terukur pada petak biru: kolom bingkai berkecerahan 106-132 dengan kejenuhan
# 100-105, sedangkan latar petak 49 dengan kejenuhan 28-60. Yang membedakan
# bukan warnanya melainkan "jauh lebih terang daripada latar petak SENDIRI,
# dan jenuh".
#
# Warna saja tetap TIDAK cukup untuk memutuskan — yang memutuskan bentuknya,
# lihat bersihkan_bingkai.
JENUH_MINIMAL = 60


def _chrome(warna, latar: float) -> bool:
    r, g, b = warna
    return ((r + g + b) / 3 > max(latar * 1.55, latar + 22)
            and max(warna) - min(warna) > JENUH_MINIMAL)


def _kekuningan(r: int, g: int, b: int) -> bool:
    """Ambang LONGGAR, hanya untuk merambat dari inti bingkai yang sudah pasti.

    Bingkai punya tepi anti-alias yang lebih redup dan zaitun. Ambang ketat
    melewatkannya, dan sisa itu masih terbaca mata sebagai bingkai walau
    hitungan piksel kuningnya sudah nol — persis yang terjadi pada
    FF-PELAJAR-6001. Ambang ini TIDAK dipakai sendirian: ia cuma boleh
    memperluas piksel yang sudah bersentuhan dengan inti bingkai, jadi barang
    berwarna hangat di tengah petak tidak bisa ikut tersapu."""
    return r > 95 and (r - b) > 30 and r >= g >= b


# Seberapa jauh dari tepi petak sebuah piksel masih dianggap bagian bingkai.
# Diukur 9 Agu pada FF-PELAJAR-6001: cincinnya masuk 4px pada petak 81x82,
# yaitu 5%. 15% memberi ruang untuk resolusi lain tanpa menjangkau tengah petak,
# tempat barang dagangan berada.
TEPI_BINGKAI = 0.15

# Berapa bagian sebuah sisi harus kuning sebelum ia disebut bingkai. Skin emas
# bisa menyentuh tepi, tapi tidak akan melapisi satu sisi penuh.
SISI_CINCIN_MINIMAL = 0.55

# Pita tepi TERSEMPIT, selalu dibersihkan tanpa syarat: barang tidak pernah
# menjangkau piksel terluar petak, jadi kuning di situ pasti chrome —
# biasanya serpihan bingkai petak tetangga.
TEPI_SERPIHAN = 0.05


def _pangkas_serpihan(rgb: Image.Image, px, w: int, h: int, latar: float) -> Image.Image:
    """Pangkas garis kuning tipis di tepi TERLUAR petak, lalu kembalikan ukuran.

    Bingkai petak tetangga sering menyisakan garis di tepi petak ini. Ia bukan
    cincin, jadi tidak tertangkap pemeriksaan bingkai — tapi ia tetap membuat
    satu petak terlihat beda sendiri, dan itu persis yang ditunjuk pemilik.

    Aman dipangkas tanpa syarat: barang dagangan tidak pernah menjangkau piksel
    terluar petak, jadi kuning di situ selalu chrome.
    """
    batas_x = max(1, int(w * TEPI_SERPIHAN))
    batas_y = max(1, int(h * TEPI_SERPIHAN))

    # 0,12 bukan 0,25: serpihan bingkai tetangga sering cuma sepotong pendek,
    # bukan garis penuh. Diukur pada FF-PELAJAR-6001 — tanda di sudut kiri-atas
    # petak 3 menjangkau 20% tinggi, lolos di ambang 25%. Aman diturunkan karena
    # yang diperiksa cuma pita TERLUAR, tempat barang dagangan tidak pernah
    # sampai; ambang ini tidak pernah menyentuh isi petak.
    def kotor_kolom(x: int) -> bool:
        return sum(1 for y in range(h) if _chrome(px[x, y], latar)) > h * 0.12

    def kotor_baris(y: int) -> bool:
        return sum(1 for x in range(w) if _chrome(px[x, y], latar)) > w * 0.12

    kiri = 0
    while kiri < batas_x and kotor_kolom(kiri):
        kiri += 1
    kanan = w
    while w - kanan < batas_x and kotor_kolom(kanan - 1):
        kanan -= 1
    atas = 0
    while atas < batas_y and kotor_baris(atas):
        atas += 1
    bawah = h
    while h - bawah < batas_y and kotor_baris(bawah - 1):
        bawah -= 1

    if (kiri, atas, kanan, bawah) == (0, 0, w, h):
        return rgb
    # Satu piksel ekstra membuang tepi anti-aliasnya.
    kiri = min(kiri + 1, batas_x) if kiri else 0
    atas = min(atas + 1, batas_y) if atas else 0
    kanan = max(kanan - 1, w - batas_x) if kanan < w else w
    bawah = max(bawah - 1, h - batas_y) if bawah < h else h
    return rgb.crop((kiri, atas, kanan, bawah)).resize((w, h), Image.Resampling.LANCZOS)


def bersihkan_bingkai(petak: Image.Image) -> Image.Image:
    """Hapus bingkai seleksi kuning dengan MEMOTONG DI DALAMNYA, bukan mengecat.

    Layar Fashion selalu menandai satu slot yang sedang dilihat dengan bingkai
    kuning, jadi di screenshot mana pun ada tepat satu petak yang terlihat beda
    sendiri.

    Mengecat ulang piksel kuningnya sempat dicoba tiga kali dan selalu
    menyisakan bayangan: bingkai punya tepi anti-alias yang meredup bertahap,
    dan ambang warna mana pun memotongnya di tengah gradasi. Yang tersisa masih
    terbaca mata sebagai bingkai walau hitungan piksel kuningnya sudah nol.

    Bingkai itu PERSEGI yang mengelilingi isi petak. Jadi isinya dipotong dari
    dalam persegi itu lalu dikembalikan ke ukuran semula — tidak ada gradasi
    yang perlu ditebak, dan hasilnya bersih sepenuhnya. Ongkosnya isi petak
    tampil ~6% lebih besar daripada petak lain, jauh lebih tidak kentara
    daripada satu petak berbingkai kuning di antara tiga yang polos.

    Yang membedakan bingkai dari barang BUKAN warnanya melainkan bentuknya:
    bingkai menempel tepi dan melapisi sisinya hampir penuh; skin senjata emas
    adalah gumpalan di tengah. Petak tanpa bingkai dikembalikan apa adanya.
    """
    rgb = petak.convert('RGB')
    w, h = rgb.size
    px = rgb.load()
    tebal_x = max(1, int(w * TEPI_BINGKAI))
    tebal_y = max(1, int(h * TEPI_BINGKAI))

    # Latar diukur dari petak ITU SENDIRI, bukan dipatok: petak gelap dan petak
    # terang punya ambang berbeda, dan memakai satu angka global membuat salah
    # satunya selalu salah.
    semua = sorted((sum(px[x, y]) / 3) for y in range(h) for x in range(w))
    latar = semua[len(semua) // 2]

    def sisi_kuning(titik) -> float:
        return sum(1 for x, y in titik if _chrome(px[x, y], latar)) / max(1, len(titik))

    sisi = [
        max(sisi_kuning([(x, y) for x in range(w)]) for y in range(tebal_y)),
        max(sisi_kuning([(x, y) for x in range(w)]) for y in range(h - tebal_y, h)),
        max(sisi_kuning([(x, y) for y in range(h)]) for x in range(tebal_x)),
        max(sisi_kuning([(x, y) for y in range(h)]) for x in range(w - tebal_x, w)),
    ]
    if sum(1 for s in sisi if s >= SISI_CINCIN_MINIMAL) < 2:
        return _pangkas_serpihan(rgb, px, w, h, latar)

    # Kotak-batas piksel kuning DI PITA TEPI saja — itu bingkainya. Kuning di
    # tengah petak (barang emas) sengaja tidak ikut, supaya ia tidak melebarkan
    # potongan dan lolos ke hasil.
    titik = [(x, y) for y in range(h) for x in range(w)
             if _chrome(px[x, y], latar)
             and (x < tebal_x or x >= w - tebal_x or y < tebal_y or y >= h - tebal_y)]
    xs = [x for x, _ in titik]
    ys = [y for _, y in titik]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)

    # Dipotong sampai kuning TERDALAM di pita tepi, bukan sampai celah pertama.
    # Percobaan yang mengukur "tebal garis" berhenti di celah gelap dan gagal
    # pada kasus nyata: petak berbingkai sering juga kena serpihan bingkai
    # TETANGGA di piksel terluar, jadi ada dua kuning dengan celah di antaranya.
    # Terukur pada FF-PELAJAR-6002: pengukur tebal cuma membuang serpihannya dan
    # meninggalkan pita bingkai selebar 4px di dalam potongan.
    def terdalam(indeks, garis, ambang=0.35):
        dalam = None
        for i_ in indeks:
            if sisi_kuning(garis(i_)) >= ambang:
                dalam = i_
        return dalam

    kolom = lambda i_: [(i_, y) for y in range(h)]
    baris = lambda i_: [(x, i_) for x in range(w)]

    dk = terdalam(range(0, tebal_x), kolom)
    dn = terdalam(range(w - 1, w - tebal_x - 1, -1), kolom)
    da = terdalam(range(0, tebal_y), baris)
    db = terdalam(range(h - 1, h - tebal_y - 1, -1), baris)

    # Satu piksel ekstra ke dalam membuang tepi anti-aliasnya.
    kiri = (dk + 2) if dk is not None else 0
    atas = (da + 2) if da is not None else 0
    kanan = (dn - 1) if dn is not None else w
    bawah = (db - 1) if db is not None else h

    if kanan - kiri < w * 0.5 or bawah - atas < h * 0.5:
        return petak

    return rgb.crop((kiri, atas, kanan, bawah)).resize((w, h), Image.Resampling.LANCZOS)


def _utuh(kal, ukuran, nomor: int) -> bool:
    _, atas, _, bawah = kotak_petak(kal, nomor)
    return atas >= 0 and bawah <= ukuran[1]


def nomor_pertama_utuh(kal, ukuran) -> int:
    """Nomor petak pertama yang seluruhnya kelihatan.

    Fase pola sering mulai di atas tepi atas gambar, jadi petak nomor 1 belum
    tentu utuh — memotongnya begitu saja menghasilkan gambar buntung.
    """
    for nomor in range(1, BATAS_PETAK + 1):
        if _utuh(kal, ukuran, nomor):
            return nomor
    raise GagalKalibrasi('tidak ada petak yang utuh di gambar ini')


def jumlah_muat(kal, ukuran) -> int:
    """Berapa petak utuh berturut-turut, dihitung dari yang pertama utuh."""
    awal = nomor_pertama_utuh(kal, ukuran)
    n = 0
    while awal + n <= BATAS_PETAK and _utuh(kal, ukuran, awal + n):
        n += 1
    return n


def potong(berkas: Path, tujuan: Path, nomor: Optional[List[int]] = None) -> List[Path]:
    im = Image.open(berkas).convert('RGB')
    kal = kalibrasi(im)
    awal = nomor_pertama_utuh(kal, im.size)
    muat = jumlah_muat(kal, im.size)

    if not nomor:
        nomor = list(range(1, muat + 1))

    tujuan = Path(tujuan)
    tujuan.mkdir(parents=True, exist_ok=True)

    dibuat = []
    for urutan, n in enumerate(nomor, start=1):
        if n < 1 or n > muat:
            raise ValueError(
                f'petak {n} tidak ada di gambar ini — yang utuh cuma 1..{muat}. '
                f'Gulir daftarnya kalau item yang kamu mau ada di bawah.')
        keluar = tujuan / f'{urutan}.png'
        # Dibersihkan SETELAH dipotong, bukan sebelum: bingkai seleksi hidup di
        # dalam satu petak, dan menghapusnya di gambar utuh berarti menebak
        # batas petaknya dua kali.
        bersihkan_bingkai(im.crop(kotak_petak(kal, awal + n - 1))).save(keluar)
        dibuat.append(keluar)
    return dibuat


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2

    berkas = Path(sys.argv[1])
    tujuan = Path(sys.argv[2])
    nomor = [int(a) for a in sys.argv[3:]]

    if not berkas.is_file():
        print(f'screenshot tidak ada: {berkas}', file=sys.stderr)
        return 1

    try:
        dibuat = potong(berkas, tujuan, nomor)
    except (GagalKalibrasi, ValueError) as e:
        print(f'BERHENTI: {e}', file=sys.stderr)
        return 1

    for p in dibuat:
        print(f'  {p}')
    print(f'\n{len(dibuat)} petak dipotong ke {tujuan}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
