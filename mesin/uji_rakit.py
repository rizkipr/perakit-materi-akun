"""Pemeriksa perkakas materi akun. Jalankan: python3 mesin/uji_rakit.py"""
from __future__ import annotations

import contextlib
import hashlib
import io
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))

import antrean
import gambar

PERIKSAAN = []


class Lewat(Exception):
    """Cek ini tidak bisa dijalankan di mesin ini, dan itu bukan kegagalan.

    Dipakai oleh cek yang butuh biner upscaler. Biner itu diunduh saat
    dibutuhkan dan sengaja tidak masuk git, jadi salinan repo yang masih
    bersih tidak memilikinya. Melaporkannya MERAH akan melatih pembaca
    mengabaikan warna merah — yang jauh lebih mahal daripada satu cek yang
    jujur mengaku tidak dijalankan.
    """


def periksa(nama):
    def bungkus(fungsi):
        PERIKSAAN.append((nama, fungsi))
        return fungsi
    return bungkus


@periksa('skala_menutup menghasilkan ukuran persis')
def _():
    # Rasio sengaja dibikin timpang ke dua arah. Jangan pakai masukan yang
    # sangat sempit terhadap slot besar (mis. 50x900 ke 2353x2521): faktor
    # skalanya 47x dan gambar antaranya menelan ratusan MB.
    for masuk, kotak in (((100, 100), (300, 200)),
                         ((4000, 100), (324, 327)),
                         ((900, 500), (2353, 2521))):
        hasil = gambar.skala_menutup(Image.new('RGBA', masuk, (255, 0, 0, 255)), *kotak)
        assert hasil.size == kotak, f'{masuk} ke {kotak} malah jadi {hasil.size}'


@periksa('skala_menutup tidak menyisakan piksel tembus di dalam slot')
def _():
    # Rasio masukan sengaja jauh berbeda dari kotaknya. Kalau dipakai
    # "muat ke dalam" dan bukan "menutup", akan ada tepi transparan.
    hasil = gambar.skala_menutup(Image.new('RGBA', (2000, 60), (0, 255, 0, 255)), 324, 327)
    alfa = hasil.getchannel('A')
    assert alfa.getextrema() == (255, 255), 'ada piksel tembus di dalam slot'


ASET = Path(__file__).parent / 'aset'
ORBITRON = str(ASET / 'Orbitron.ttf')
KOTAK_ISIAN = (100, 100, 563, 155)   # ukuran nyata isian Kode Akun di template


@periksa('teks pendek memakai ukuran awal')
def _():
    kanvas = Image.new('RGBA', (800, 400), (0, 0, 0, 255))
    dipakai = gambar.teks_di_kotak(kanvas, KOTAK_ISIAN, '5001',
                                   ORBITRON, (255, 255, 255, 255), 92, variasi='Bold')
    assert dipakai == 92, f'ukuran turun jadi {dipakai} padahal teksnya pendek'


@periksa('teks panjang mengecil dan tetap di dalam kotak')
def _():
    kanvas = Image.new('RGBA', (800, 400), (0, 0, 0, 255))
    panjang = '999.999.999.999'
    dipakai = gambar.teks_di_kotak(kanvas, KOTAK_ISIAN, panjang, ORBITRON,
                                   (255, 255, 255, 255), 92, variasi='Bold')
    assert dipakai < 92, 'teks panjang tidak mengecil'

    font = gambar.muat_font(ORBITRON, dipakai, 'Bold')
    from PIL import ImageDraw
    kiri, atas, kanan, bawah = ImageDraw.Draw(kanvas).textbbox((0, 0), panjang, font=font)
    # Dikali gambar.JEDA (bukan KOTAK_ISIAN mentah): isian pada template punya
    # tepi bercahaya yang ikut termakan, jadi batas sungguhannya lebih sempit
    # dari lebar kotak. Kalau dites terhadap KOTAK_ISIAN mentah, sebuah
    # regresi yang menghapus perkalian JEDA di loop shrink-nya sendiri tidak
    # akan pernah tertangkap — teks yang penuh sampai tepi kotak tetap lolos.
    assert kanan - kiri <= KOTAK_ISIAN[2] * gambar.JEDA, 'teks masih meluber melewati lebar isian (termasuk jeda tepi)'
    assert bawah - atas <= KOTAK_ISIAN[3] * gambar.JEDA, 'teks masih meluber melewati tinggi isian (termasuk jeda tepi)'


@periksa('teks benar-benar tergambar di dalam kotak, bukan di luarnya')
def _():
    kanvas = Image.new('RGBA', (800, 400), (0, 0, 0, 255))
    gambar.teks_di_kotak(kanvas, KOTAK_ISIAN, '5001', ORBITRON,
                         (255, 255, 255, 255), 92, variasi='Bold')
    x, y, w, h = KOTAK_ISIAN
    di_dalam = kanvas.crop((x, y, x + w, y + h)).convert('L').getextrema()[1]
    assert di_dalam > 200, 'tidak ada piksel terang di dalam kotak — teks tidak tergambar di sana'


@periksa('variasi Bold sungguh diterapkan, bukan diabaikan diam-diam')
def _():
    # Orbitron hanya tersedia sebagai font variabel. Kalau set_variation_by_name
    # gagal tanpa suara, semua angka tercetak Regular dan tak ada yang tahu
    # sampai 30 kartu jadi. Lebar hampir tak berubah antar bobot pada font ini,
    # jadi yang dihitung TINTA-nya, bukan kotak-batasnya.
    def tinta(variasi):
        im = Image.new('L', (700, 160), 0)
        from PIL import ImageDraw
        ImageDraw.Draw(im).text((10, 20), '750.000',
                                font=gambar.muat_font(ORBITRON, 92, variasi), fill=255)
        return sum(1 for p in im.getdata() if p > 128)

    polos, tebal = tinta(None), tinta('Bold')
    assert tebal > polos * 1.08, f'Bold hampir sama dengan Regular ({polos} vs {tebal})'


def _buat_akun(akar, tingkat, kode, n_item=4, n_slide=4, n_karakter=3,
               harga='750.000', poster=False):
    folder = akar / tingkat / kode
    for sub, n in (('karakter', n_karakter), ('item', n_item), ('slide', n_slide)):
        (folder / sub).mkdir(parents=True, exist_ok=True)
        for i in range(1, n + 1):
            Image.new('RGBA', (60, 60), (255, 0, 0, 255)).save(folder / sub / f'{i}.png')
    if harga is not None:
        (folder / 'info.txt').write_text(f'harga: {harga}\n')
    if poster:
        Image.new('RGBA', (400, 500), (0, 0, 255, 255)).save(folder / 'poster.png')
    return folder


@periksa('folder lengkap terbaca beserta tingkat, kode, dan harga')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        _buat_akun(akar, 'premium', '5001')
        akun, dilewati = antrean.baca(akar)
        assert dilewati == [], f'ada yang dilewati padahal lengkap: {dilewati}'
        assert len(akun) == 1
        a = akun[0]
        assert a.kode == '5001' and a.tingkat == 'premium' and a.harga == '750.000'
        assert len(a.item) == 4 and len(a.slide) == 4 and len(a.karakter) == 3


@periksa('premium berlabel Sultan, bukan Premium')
def _():
    assert antrean.LABEL_TINGKAT['premium'] == 'Sultan'


@periksa('item kurang dari empat dilewati DAN tercatat')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        _buat_akun(akar, 'premium', '5001', n_item=3)
        akun, dilewati = antrean.baca(akar)
        assert akun == [], 'folder cacat malah ikut dirakit'
        assert len(dilewati) == 1, 'folder dilewati tanpa tercatat'
        assert '5001' in dilewati[0][0] and 'item' in dilewati[0][1].lower()


@periksa('slide berjumlah ganjil dilewati dan pesannya menyebut jalan keluar')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        _buat_akun(akar, 'reguler', '5002', n_slide=5)
        akun, dilewati = antrean.baca(akar)
        assert akun == []
        alasan = dilewati[0][1]
        assert '5' in alasan and ('tambah' in alasan or 'kurangi' in alasan), \
            f'pesan tidak memberi jalan keluar: {alasan}'


@periksa('sepuluh berkas slide terurut alami, bukan 1-10-2')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        _buat_akun(akar, 'premium', '5010', n_slide=10)
        akun, dilewati = antrean.baca(akar)
        assert dilewati == [], dilewati
        urut = [b.stem for b in akun[0].slide]
        assert urut == [str(i) for i in range(1, 11)], f'urutan kacau: {urut}'


@periksa('info.txt hilang dilewati, bukan dianggap harga kosong')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        _buat_akun(akar, 'pelajar', '5003', harga=None)
        akun, dilewati = antrean.baca(akar)
        assert akun == []
        alasan = dilewati[0][1].lower()
        assert 'tidak ada' in alasan, f'pesan tidak bilang file tidak ada: {alasan}'
        assert 'kosong' not in alasan, f'file hilang malah dikira harga kosong: {alasan}'


@periksa('info.txt dengan spasi di depan "harga:" tetap terbaca')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        folder = _buat_akun(akar, 'reguler', '5006', harga=None)
        (folder / 'info.txt').write_text('  harga: 750.000\n')
        akun, dilewati = antrean.baca(akar)
        assert dilewati == [], f'baris berspasi di depan malah dilewati: {dilewati}'
        assert akun[0].harga == '750.000'


@periksa('info.txt tanpa baris "harga:" dan "harga:" kosong dapat pesan berbeda')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        folder_a = _buat_akun(akar, 'reguler', '5007', harga=None)
        (folder_a / 'info.txt').write_text('catatan: belum ada harga\n')
        folder_b = _buat_akun(akar, 'reguler', '5008', harga=None)
        (folder_b / 'info.txt').write_text('harga:\n')
        akun, dilewati = antrean.baca(akar)
        assert akun == []
        alasan = {nama.split('/')[1]: pesan for nama, pesan in dilewati}
        assert alasan['5007'] != alasan['5008'], \
            f'tanpa-baris dan kosong dapat pesan sama: {alasan}'
        assert 'kosong' in alasan['5008'].lower(), alasan['5008']


@periksa('info.txt UTF-16 (disimpan TextEdit) melewatkan akunnya, bukan menjatuhkan jalannya')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        _buat_akun(akar, 'reguler', '5009', harga=None)
        (akar / 'reguler' / '5009' / 'info.txt').write_text('harga: 750.000\n', encoding='utf-16')
        akun, dilewati = antrean.baca(akar)
        assert akun == [], 'info.txt UTF-16 malah terbaca sebagai harga sah'
        assert len(dilewati) == 1


@periksa('poster.png yang ada dipakai, karakter tidak diwajibkan')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        _buat_akun(akar, 'premium', '5004', n_karakter=0, poster=True)
        akun, dilewati = antrean.baca(akar)
        assert dilewati == [], f'poster ada tapi tetap dilewati: {dilewati}'
        assert akun[0].poster is not None


@periksa('companion AppleDouble (._1.png) tidak ikut terhitung sebagai gambar')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        folder = _buat_akun(akar, 'premium', '5011')
        # Menyalin lewat exFAT atau langsung dari HP meninggalkan companion
        # tak kasat mata di Finder ini — di sebelah tiap gambar sungguhan.
        for i in range(1, 5):
            (folder / 'item' / f'._{i}.png').write_bytes(b'AppleDouble palsu')
        akun, dilewati = antrean.baca(akar)
        assert dilewati == [], f'companion titik bikin folder sehat dilewati: {dilewati}'
        assert len(akun[0].item) == 4, f'companion ikut terhitung: {len(akun[0].item)}'


@periksa('kode akun yang sama di dua tingkat menghentikan seluruh jalannya')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        # Nama berkas keluaran cuma pakai kode ("5001-utama.webp"), jadi dua
        # folder dengan kode sama di tingkat berbeda akan menimpa berkas yang
        # sama — ringkasan tetap melaporkan angka yang seolah benar.
        _buat_akun(akar, 'premium', '5001')
        _buat_akun(akar, 'reguler', '5001')
        try:
            antrean.baca(akar)
        except antrean.GalatFatal as e:
            assert 'premium/5001' in str(e) and 'reguler/5001' in str(e), \
                f'pesan tidak menyebut kedua folder: {e}'
        else:
            raise AssertionError('kode dobel lintas tingkat malah lolos diam-diam')


@periksa('nama folder tingkat yang tidak sah menghentikan seluruh jalannya')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        _buat_akun(akar, 'sultan', '5005')   # 'sultan' label, bukan nilai DB
        try:
            antrean.baca(akar)
        except antrean.GalatFatal as e:
            assert 'sultan' in str(e) and 'premium' in str(e), \
                'pesan tidak menyebut folder yang salah dan nilai yang sah'
        else:
            raise AssertionError('tingkat tak dikenal malah diterima diam-diam')


import template


def _akun_contoh(akar):
    _buat_akun(akar, 'premium', '5001', poster=True)
    akun, _ = antrean.baca(akar)
    return akun[0]


@periksa('kartu utama berukuran kanvas penuh')
def _():
    with tempfile.TemporaryDirectory() as t:
        a = _akun_contoh(Path(t))
        kartu = template.rakit_kartu_utama(a, Image.open(a.poster), ASET)
        assert kartu.size == template.KANVAS, f'ukuran kanvas {kartu.size}'


@periksa('setiap slot kartu utama terisi — tidak ada yang masih tembus')
def _():
    with tempfile.TemporaryDirectory() as t:
        a = _akun_contoh(Path(t))
        kartu = template.rakit_kartu_utama(a, Image.open(a.poster), ASET)
        for nama, (x, y, w, h) in [('jendela utama', template.JENDELA_UTAMA)] + \
                [(f'slot item {i+1}', k) for i, k in enumerate(template.SLOT_ITEM)]:
            alfa = kartu.getpixel((x + w // 2, y + h // 2))[3]
            assert alfa == 255, f'{nama} masih tembus (alfa {alfa}) — isinya tidak mendarat'


@periksa('ornamen bingkai tidak tertimpa isi')
def _():
    with tempfile.TemporaryDirectory() as t:
        a = _akun_contoh(Path(t))
        kartu = template.rakit_kartu_utama(a, Image.open(a.poster), ASET)
        bingkai = Image.open(ASET / 'template-1.png').convert('RGBA')
        # Titik di LUAR semua kotak isi: menjaga isi tidak bocor ke luar
        # slotnya, tapi tidak bisa membedakan urutan tempel (isi di depan atau
        # di belakang bingkai) karena tempelan isi tidak pernah menyentuhnya.
        luar = ((90, 250), (20, 20), (2590, 3240))
        # Titik di DALAM JENDELA_UTAMA, pada ornamen api yang menjorok opak ke
        # area gambar — satu-satunya yang bisa membuktikan isi ditempel di
        # BELAKANG bingkai, bukan di atasnya. Kalau isi ditempel di atas,
        # ornamen di sini akan tertimpa poster dan titik-titik ini berubah;
        # titik di luar jendela tidak akan pernah menangkap itu.
        dalam = ((250, 285), (2362, 2562))
        for titik in luar:
            assert kartu.getpixel(titik) == bingkai.getpixel(titik), \
                f'ornamen di luar jendela {titik} berubah — isi bocor keluar slot'
        for titik in dalam:
            assert kartu.getpixel(titik) == bingkai.getpixel(titik), \
                f'ornamen DI DALAM jendela {titik} berubah — isi menimpa bingkai'


@periksa('label tingkat premium tertulis Sultan')
def _():
    with tempfile.TemporaryDirectory() as t:
        a = _akun_contoh(Path(t))
        polos = template.rakit_kartu_utama(a, Image.open(a.poster), ASET, tulis_teks=False)
        penuh = template.rakit_kartu_utama(a, Image.open(a.poster), ASET)
        x, y, w, h = template.ISIAN_TINGKAT
        kotak = (x, y, x + w, y + h)
        assert list(polos.crop(kotak).getdata()) != list(penuh.crop(kotak).getdata()), \
            'isian tingkat tidak berubah — label tidak ditulis'
        assert a.label_tingkat == 'Sultan'

        # Dua tes di atas tidak membuktikan KATA yang tertulis — hanya bahwa
        # sesuatu berubah, dan bahwa properti Akun itu sendiri (bukan yang
        # digambar) bernilai 'Sultan'. Kalau kode salah kirim akun.tingkat
        # ('premium', nilai mentah DB) ke teks_di_kotak, kedua tes di atas
        # tetap lulus. Render dua kandidat kata dengan pemanggilan yang
        # sama persis dengan jalur produksi, lalu cocokkan potongannya.
        poppins = str(ASET / 'Poppins-Bold.ttf')
        render_sultan = polos.copy()
        gambar.teks_di_kotak(render_sultan, template.ISIAN_TINGKAT, 'Sultan',
                             poppins, template.PUTIH, template.UKURAN_TINGKAT)
        render_mentah = polos.copy()
        gambar.teks_di_kotak(render_mentah, template.ISIAN_TINGKAT, a.tingkat,
                             poppins, template.PUTIH, template.UKURAN_TINGKAT)

        assert list(penuh.crop(kotak).getdata()) == list(render_sultan.crop(kotak).getdata()), \
            'isian tingkat tidak cocok dengan kata "Sultan" — kata yang tertulis salah'
        assert list(penuh.crop(kotak).getdata()) != list(render_mentah.crop(kotak).getdata()), \
            'isian tingkat malah cocok dengan nilai mentah tingkat ("premium") — label tidak dipakai'


@periksa('ekspor menghasilkan ukuran EKSPOR persis, bukan kanvas mentah')
def _():
    # Dulu mematok (1080, 1350) sebagai angka mentah, jadi ia merah tiap
    # ukuran ekspornya disetel — padahal yang dijaga bukan angkanya,
    # melainkan bahwa ekspor() benar-benar menghormati konstantanya dan
    # tidak diam-diam menyimpan kanvas 2613x3264 apa adanya. Batas 4:5 dan
    # ambang bawahnya dijaga cek 'ekspor tidak membuang hasil upscaler'.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        a = _akun_contoh(akar)
        kartu = template.rakit_kartu_utama(a, Image.open(a.poster), ASET)
        keluar = akar / 'hasil.webp'
        template.ekspor(kartu, keluar)
        assert Image.open(keluar).size == template.EKSPOR, Image.open(keluar).size
        assert Image.open(keluar).size != template.KANVAS, \
            'kanvas disimpan apa adanya — ekspor() tidak mengecilkan sama sekali'


@periksa('kartu slide mengisi kedua jendela')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        a = _akun_contoh(akar)
        kartu = template.rakit_kartu_slide(a.slide[:2], ASET)
        assert kartu.size == template.KANVAS
        for i, (x, y, w, h) in enumerate(template.JENDELA_SLIDE):
            alfa = kartu.getpixel((x + w // 2, y + h // 2))[3]
            assert alfa == 255, f'jendela slide {i+1} masih tembus'


@periksa('kartu slide menolak pasangan yang bukan dua berkas')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        a = _akun_contoh(akar)
        for jumlah in (1, 3):
            try:
                template.rakit_kartu_slide(a.slide[:jumlah], ASET)
            except ValueError:
                pass
            else:
                raise AssertionError(f'{jumlah} berkas malah diterima')


@periksa('enam berkas slide jadi tiga pasang, empat jadi dua')
def _():
    assert len(template.pasangkan(list(range(6)))) == 3
    assert len(template.pasangkan(list(range(4)))) == 2
    assert template.pasangkan(list(range(4))) == [[0, 1], [2, 3]]


import rakit


@periksa('satu akun lengkap menghasilkan kartu utama dan kartu slide')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        _buat_akun(akar, 'premium', '5001', n_slide=4, poster=True)
        dibuat, dilewati, peringatan, _ = rakit.jalankan(akar, tujuan, ASET)
        assert dilewati == [], dilewati
        assert peringatan == [], peringatan
        nama = sorted(p.name for p in dibuat)
        assert nama == ['5001-slide-1.webp', '5001-slide-2.webp', '5001-utama.webp'], nama
        for p in dibuat:
            assert Image.open(p).size == template.EKSPOR


@periksa('kartu jadi masuk folder per akun, dan salinan datar versi lama terbuang')
def _():
    # Sampai 14 Agu seluruh kartu berserak di akar siap-upload. Dengan tiga
    # puluh akun itu 120 berkas dalam satu daftar, dan mengunggah satu akun
    # berarti memungut berkasnya satu per satu di antara berkas akun lain.
    #
    # Nama berkas sengaja TIDAK dipendekkan: kodenya tetap menempel supaya
    # berkas yang terlanjur diseret keluar folder masih punya identitas.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        _buat_akun(akar, 'premium', '5001', n_slide=4, poster=True)

        # Sisa versi lama, datar di akar. Kalau ia tidak ikut dibuang, lari
        # pertama sesudah perubahan ini meninggalkan dua salinan di dua tempat
        # tanpa tanda mana yang basi — persis kegagalan yang penjaga sisa lari
        # sebelumnya dibuat untuk mencegah.
        tujuan.mkdir(parents=True, exist_ok=True)
        basi = tujuan / '5001-utama.webp'
        Image.new('RGB', (10, 10), (0, 0, 0)).save(basi, 'WEBP')

        dibuat, dilewati, _, _ = rakit.jalankan(akar, tujuan, ASET)
        assert dilewati == [], dilewati

        folder = tujuan / '5001'
        luar = [p for p in dibuat if p.parent != folder]
        assert not luar, f'kartu tidak masuk folder akunnya: {luar}'
        assert sorted(p.name for p in folder.iterdir()) == \
            ['5001-slide-1.webp', '5001-slide-2.webp', '5001-utama.webp'], \
            sorted(p.name for p in folder.iterdir())
        assert not basi.exists(), \
            'salinan datar sisa versi lama tetap tinggal di akar — pemilik punya dua salinan'


@periksa('akun yang kartunya sudah ada tidak dirakit ulang')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        _buat_akun(akar, 'premium', '5001', poster=True)

        dibuat1, dilewati1, _, sudah1 = rakit.jalankan(akar, tujuan, ASET)
        assert dilewati1 == [] and dibuat1, (dilewati1, dibuat1)
        assert sudah1 == [], f'lari pertama mengaku sudah ada: {sudah1}'
        jam = {p: p.stat().st_mtime_ns for p in dibuat1}

        dibuat2, dilewati2, _, sudah2 = rakit.jalankan(akar, tujuan, ASET)
        assert dibuat2 == [], f'kartunya dibuat ulang padahal sudah ada: {dibuat2}'
        assert dilewati2 == [], dilewati2
        # Daftarnya sendiri, bukan digabung ke DILEWATI: keduanya beda arti dan
        # beda tindakan. DILEWATI berarti folder antreannya kurang dan harus
        # diperbaiki; yang ini berarti kartunya memang sudah ada. Digabung,
        # sepuluh baris "sudah ada" menenggelamkan satu folder yang rusak.
        assert sudah2 == ['premium/5001'], sudah2
        for berkas, sebelum in jam.items():
            assert berkas.stat().st_mtime_ns == sebelum, \
                f'{berkas.name} ditulis ulang padahal akunnya dilewati'


@periksa('folder keluaran yang kosong bukan hasil selesai — akunnya tetap dirakit')
def _():
    # Lari yang mati di tengah meninggalkan folder tanpa isi. Kalau
    # KEBERADAAN folder yang dipakai sebagai penanda selesai, akun itu tidak
    # akan pernah jadi lagi tanpa pemilik menghapus foldernya sendiri — dan ia
    # tidak punya cara tahu foldernya kosong di antara tiga puluh yang lain.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        _buat_akun(akar, 'premium', '5001', poster=True)
        rakit.jalankan(akar, tujuan, ASET)

        for berkas in (tujuan / '5001').iterdir():
            berkas.unlink()

        dibuat, _, _, sudah = rakit.jalankan(akar, tujuan, ASET)
        assert sudah == [], f'folder kosong dianggap hasil yang selesai: {sudah}'
        assert dibuat, 'akun dengan folder keluaran kosong tidak dirakit ulang'


@periksa('ulang=True merakit ulang walau kartunya sudah ada')
def _():
    # Jalan keluarnya waktu MESINnya yang berubah. Penanda "sudah ada" cuma
    # melihat folder keluaran, jadi menyetel poster.py atau mengganti latar
    # tidak akan menyebar sendiri ke kartu yang terlanjur jadi.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        _buat_akun(akar, 'premium', '5001', poster=True)

        dibuat1, _, _, _ = rakit.jalankan(akar, tujuan, ASET)
        jam = {p: p.stat().st_mtime_ns for p in dibuat1}

        dibuat2, _, _, sudah = rakit.jalankan(akar, tujuan, ASET, ulang=True)
        assert sudah == [], f'ulang=True masih melewati akun: {sudah}'
        assert sorted(p.name for p in dibuat2) == sorted(p.name for p in dibuat1)
        tetap = [p.name for p in dibuat2 if p.stat().st_mtime_ns == jam.get(p)]
        assert tetap == [], \
            f'ulang=True tidak menulis ulang seluruh kartu: yang tidak tersentuh {tetap}'


@periksa('bendera --ulang diterima main(), dan akun yang sudah ada punya bagian sendiri di ringkasan')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        _buat_akun(akar, 'premium', '5001', poster=True)

        # ASET di berkas cek ini dan rakit.ASET_BAWAAN menunjuk folder yang
        # sama (mesin/aset), jadi main() yang memakai bawaannya tetap sah.
        argv_asli = sys.argv
        try:
            sys.argv = ['rakit.py', str(akar), str(tujuan)]
            assert rakit.main() == 0

            keluar = io.StringIO()
            with contextlib.redirect_stdout(keluar):
                assert rakit.main() == 0
            cetak = keluar.getvalue()
            assert 'sudah ada' in cetak and '5001' in cetak, \
                f'akun yang dilewati tidak tercetak: {cetak!r}'
            assert 'DILEWATI' not in cetak, \
                f'akun yang sudah ada malah dilaporkan sebagai DILEWATI: {cetak!r}'

            sys.argv = ['rakit.py', str(akar), str(tujuan), '--ulang']
            keluar = io.StringIO()
            with contextlib.redirect_stdout(keluar):
                assert rakit.main() == 0
            assert '3 berkas dibuat' in keluar.getvalue(), \
                f'--ulang tidak merakit ulang: {keluar.getvalue()!r}'
        finally:
            sys.argv = argv_asli


@periksa('folder cacat dilewati tapi folder sehat tetap jadi')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        _buat_akun(akar, 'premium', '5001', poster=True)
        _buat_akun(akar, 'premium', '5002', n_item=2, poster=True)
        dibuat, dilewati, _, _ = rakit.jalankan(akar, tujuan, ASET)
        assert any('5001-utama' in p.name for p in dibuat), 'folder sehat ikut mati'
        assert len(dilewati) == 1 and '5002' in dilewati[0][0]


@periksa('poster berasio jauh melahirkan peringatan, kartunya tetap dibuat')
def _():
    # Poster mentah Gemini keluar tegak (604x1024, rasio 0,59) sementara jendela
    # utama 0,93. Diukur 8 Agu: 37% tingginya terbuang — kepala atau kaki
    # karakter hilang. Kartu tetap dibuat, tapi tidak boleh diam-diam.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        folder = _buat_akun(akar, 'premium', '5001', poster=True)
        Image.new('RGBA', (604, 1024), (0, 0, 255, 255)).save(folder / 'poster.png')
        dibuat, dilewati, peringatan, _ = rakit.jalankan(akar, tujuan, ASET)
        assert dilewati == [], dilewati
        assert any('5001-utama' in p.name for p in dibuat), 'kartu malah tidak dibuat'
        assert len(peringatan) == 1, f'potongan 37% lewat tanpa peringatan: {peringatan}'
        assert '%' in peringatan[0][1], 'peringatan tidak menyebut berapa yang hilang'


@periksa('aset template yang hilang menghentikan seluruh jalannya')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        _buat_akun(akar, 'premium', '5001', poster=True)
        kosong = Path(t) / 'aset-kosong'
        kosong.mkdir()
        try:
            rakit.jalankan(akar, Path(t) / 'keluar', kosong)
        # Diketatkan ke GalatFatal saja (bukan juga FileNotFoundError):
        # template._bingkai melempar FileNotFoundError sendiri kalau
        # preflight-nya dihapus, jadi except yang longgar tetap hijau
        # walau pesan "BERHENTI: ..." yang bisa ditindaklanjuti sudah hilang.
        except antrean.GalatFatal:
            pass
        else:
            raise AssertionError('aset hilang malah dilewati diam-diam')


@periksa('font Poppins-Bold.ttf hilang sendirian tetap menghentikan seluruh jalannya')
def _():
    # Preflight adalah SATU-SATUNYA penjaga dua berkas font. Kalau cuma
    # template-1/2.png dan Orbitron.ttf yang dicek, folder ini lolos
    # preflight lalu OSError mentah dari Pillow baru muncul di tengah render.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        _buat_akun(akar, 'premium', '5001', poster=True)
        aset_tanpa_font = Path(t) / 'aset-tanpa-font'
        shutil.copytree(ASET, aset_tanpa_font)
        (aset_tanpa_font / 'Poppins-Bold.ttf').unlink()
        try:
            rakit.jalankan(akar, Path(t) / 'keluar', aset_tanpa_font)
        except antrean.GalatFatal:
            pass
        else:
            raise AssertionError('font Poppins-Bold.ttf hilang malah lolos tanpa GalatFatal')


@periksa('akun tanpa poster.png minta GalatAkun (per-akun), bukan GalatFatal (seluruh jalan)')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        # karakter/ lengkap 3 gambar → lolos antrean._periksa. Gagalnya baru
        # ketahuan saat DIRAKIT, lewat cabang ImportError di _poster_untuk.
        _buat_akun(akar, 'premium', '5001', n_karakter=3, poster=False)
        akun, dilewati = antrean.baca(akar)
        assert dilewati == [], dilewati

        # Begitu poster.py ada (Task 8), `import poster` di _poster_untuk
        # sungguhan berhasil dan cabang ImportError ini tidak pernah lagi
        # tertembus lewat skenario nyata. Tes ini menjaga cabangnya tetap
        # benar SEBAGAI KODE (mis. kalau poster.py suatu saat rusak/terhapus)
        # tanpa bergantung pada ada-tidaknya berkas itu di disk — dipaksa
        # lewat sys.modules, bukan lewat menghapus berkas nyata.
        modul_asli = sys.modules.pop('poster', None)
        sys.modules['poster'] = None
        try:
            try:
                rakit._poster_untuk(akun[0], ASET)
            except antrean.GalatAkun:
                pass
            except antrean.GalatFatal:
                raise AssertionError('poster hilang salah pakai GalatFatal — akun lain ikut kena')
            else:
                raise AssertionError('poster hilang tidak memicu galat sama sekali')
        finally:
            del sys.modules['poster']
            if modul_asli is not None:
                sys.modules['poster'] = modul_asli


@periksa('poster.py tak bisa diimpor: akun berposter sendiri tetap jadi, akun yang butuh Perkakas B dilewati, jalannya tidak mati')
def _():
    # Finding R2: `import poster` di preflight rakit.jalankan (bukan di
    # _poster_untuk) tadinya TANPA penjaga. _poster_untuk sudah lama menjaga
    # invariannya sendiri (cek di atas) — docstring-nya menjanjikan Perkakas A
    # tetap jalan penuh kalau B tidak ada. Tapi preflight yang tak dijaga
    # membuat ModuleNotFoundError MENTAH menembus sampai main(), yang cuma
    # menangkap GalatFatal — kegagalan paling buruk di seluruh perkakas ini:
    # bukan skip per-akun, bukan GalatFatal yang rapi, tapi traceback Python
    # tanpa ringkasan sama sekali. sys.modules dipaksa (teknik yang sama
    # seperti cek di atas), bukan berkas dihapus, supaya deterministik di
    # mesin mana pun terlepas dari apakah poster.py sungguh ada di checkout
    # ini.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        _buat_akun(akar, 'premium', '5001', poster=True)                  # posternya sendiri
        _buat_akun(akar, 'reguler', '5002', n_karakter=3, poster=False)   # butuh Perkakas B

        modul_asli = sys.modules.pop('poster', None)
        sys.modules['poster'] = None
        try:
            dibuat, dilewati, _, _ = rakit.jalankan(akar, tujuan, ASET)
        finally:
            del sys.modules['poster']
            if modul_asli is not None:
                sys.modules['poster'] = modul_asli

        assert any('5001-utama' in p.name for p in dibuat), \
            f'akun berposter sendiri ikut mati padahal poster.py tak bisa diimpor: dibuat={dibuat}'
        assert len(dilewati) == 1 and '5002' in dilewati[0][0], \
            f'akun yang butuh Perkakas B tidak tercatat dilewati: {dilewati}'


@periksa('akun tanpa poster.png dilewati saat dirakit, akun sehat sesudahnya tetap jadi')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        # 'premium' < 'reguler' — 5001 diproses lebih dulu, gagal duluan.
        _buat_akun(akar, 'premium', '5001', n_karakter=3, poster=False)
        _buat_akun(akar, 'reguler', '5002', poster=True)
        dibuat, dilewati, _, _ = rakit.jalankan(akar, tujuan, ASET)
        assert any('5002-utama' in p.name for p in dibuat), \
            'akun sehat sesudahnya ikut mati padahal 5001 gagal duluan'
        assert len(dilewati) == 1 and '5001' in dilewati[0][0], dilewati
        assert 'gagal saat merakit' in dilewati[0][1], \
            f'alasan tidak ditandai sebagai gagal-rakit: {dilewati[0][1]}'


@periksa('berkas gambar rusak (nol byte) melewatkan akunnya, bukan menjatuhkan seluruh jalannya')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        folder = _buat_akun(akar, 'premium', '5001', poster=True)
        # Screenshot yang masih disalin dari HP: file ada tapi isinya nol byte.
        (folder / 'item' / '3.png').write_bytes(b'')
        _buat_akun(akar, 'reguler', '5002', poster=True)
        dibuat, dilewati, _, _ = rakit.jalankan(akar, tujuan, ASET)
        assert any('5002-utama' in p.name for p in dibuat), \
            'akun sehat ikut mati gara-gara berkas rusak di akun lain'
        assert len(dilewati) == 1 and '5001' in dilewati[0][0], dilewati
        assert 'gagal saat merakit' in dilewati[0][1], dilewati[0][1]


@periksa('poster berasio jauh yang lalu gagal merakit tidak nongol di PERINGATAN')
def _():
    # Regresi: peringatan potongan poster dicatat SEBELUM rakit_kartu_utama
    # dipanggil, tapi ikon item baru dibuka DI DALAM rakit_kartu_utama. Kalau
    # ikon itemnya rusak, build gagal SESUDAH peringatan sudah tercatat — akun
    # itu nongol di dua daftar sekaligus: PERINGATAN ("kartunya tetap dibuat")
    # dan DILEWATI. Itu bohong: kartunya tidak pernah jadi.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        folder = _buat_akun(akar, 'premium', '5003', poster=True)
        Image.new('RGBA', (604, 1024), (0, 0, 255, 255)).save(folder / 'poster.png')
        (folder / 'item' / '3.png').write_bytes(b'')   # ikon rusak — trigger build gagal
        dibuat, dilewati, peringatan, _ = rakit.jalankan(akar, tujuan, ASET)
        assert len(dilewati) == 1 and '5003' in dilewati[0][0], dilewati
        kode_peringatan = [kode for kode, _ in peringatan]
        assert '5003' not in kode_peringatan, \
            f'5003 gagal dirakit tapi tetap nongol di PERINGATAN: {peringatan}'


@periksa('ringkasan tetap tercetak walau GalatFatal menembus main()')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        _buat_akun(akar, 'siluman', '5099', poster=True)   # nama tingkat tak sah

        argv_asli = sys.argv
        sys.argv = ['rakit.py', str(akar), str(tujuan)]
        keluar_stdout, keluar_stderr = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(keluar_stdout), \
                 contextlib.redirect_stderr(keluar_stderr):
                kode = rakit.main()
        finally:
            sys.argv = argv_asli

        assert kode != 0, 'exit code tetap 0 padahal GalatFatal menembus'
        assert 'berkas dibuat' in keluar_stdout.getvalue(), \
            f'ringkasan hilang saat GalatFatal menembus: {keluar_stdout.getvalue()!r}'
        assert 'BERHENTI' in keluar_stderr.getvalue(), keluar_stderr.getvalue()


import subprocess

POTONG = Path(__file__).parent / 'potong'


def _butuh_potong(sistem: str = sys.platform, biner: Path = POTONG) -> None:
    """Lewati cek yang butuh biner potong kalau mesin ini tidak bisa punya.

    Dua ketiadaan yang berbeda, dan membedakannya itu seluruh gunanya. Di
    macOS binernya BISA dikompilasi, jadi ketiadaannya kesalahan yang bisa
    langsung diperbaiki — merah, dengan perintahnya tercetak. Di Windows dan
    Linux tidak ada swiftc dan tidak ada Vision, jadi merah di sana menyuruh
    hal yang mustahil dan melatih pembaca mengabaikan warna merah, persis yang
    diperingatkan docstring Lewat.
    """
    if sistem != 'darwin':
        raise Lewat('pemotong Vision cuma ada di macOS')
    if not biner.exists():
        # Pesan sama seperti poster._potong: checkout baru tidak punya cara
        # keluar tanpa ini — binernya sengaja digitignore, jadi cek-cek ini
        # gagal di setiap checkout baru sampai baris ini dijalankan sekali.
        raise AssertionError(
            f'biner potong belum dikompilasi: {biner}. '
            f'Jalankan: swiftc -O -o {biner} {biner}.swift')


@periksa('cek berbiner-potong dilewati di luar macOS, bukan dilaporkan merah')
def _():
    try:
        _butuh_potong('win32')
    except Lewat:
        pass
    except AssertionError as e:
        raise AssertionError(
            f'di Windows cek ini merah dan menyuruh mengompilasi Swift — '
            f'mustahil di sana: {e}')
    else:
        raise AssertionError('tidak dilewati padahal di luar macOS')


@periksa('cek berbiner-potong tetap merah di macOS kalau binernya belum dikompilasi')
def _():
    # Path yang dijamin tidak ada, bukan POTONG sungguhan. Versi pertama cek
    # ini menyerah lewat Lewat kalau binernya kebetulan sudah dikompilasi —
    # artinya di mesin yang siap merakit, justru cabang ini tidak pernah
    # teruji, dan satu-satunya yang bisa membuatnya jalan lagi adalah menghapus
    # biner yang baru saja susah payah dibuat.
    tak_ada = Path(tempfile.gettempdir()) / 'potong-yang-tidak-pernah-ada'
    assert not tak_ada.exists(), f'{tak_ada} malah ada — pilih nama lain'
    try:
        _butuh_potong('darwin', tak_ada)
    except Lewat as e:
        raise AssertionError(
            f'di macOS ketiadaan biner dilewati diam-diam, padahal bisa '
            f'dikompilasi: {e}')
    except AssertionError as e:
        assert 'swiftc' in str(e), f'pesannya tidak menyebut cara memperbaiki: {e}'


@periksa('preflight menawarkan poster.png di luar macOS, bukan menyuruh swiftc')
def _():
    pesan = rakit._galat_pemotong('win32', biner_ada=False)
    assert pesan is not None, 'jalur karakter/ diloloskan di mesin tanpa Vision'
    assert 'poster.png' in pesan, \
        f'pemilik tidak diberi jalan keluar yang bisa ia tempuh: {pesan}'
    assert 'swiftc' not in pesan, \
        f'menyuruh swiftc di mesin yang tidak punya Swift: {pesan}'


@periksa('preflight tetap menyuruh swiftc di macOS kalau binernya belum ada')
def _():
    pesan = rakit._galat_pemotong('darwin', biner_ada=False)
    assert pesan is not None, 'biner hilang malah diloloskan'
    assert 'swiftc' in pesan, f'pesannya tidak menyebut cara memperbaiki: {pesan}'


@periksa('preflight meloloskan macOS yang binernya sudah dikompilasi')
def _():
    assert rakit._galat_pemotong('darwin', biner_ada=True) is None, \
        'mesin yang siap merakit malah ditahan'


@periksa('preflight menahan Windows walau ada berkas bernama potong')
def _():
    # Biner Mach-O yang kebawa lewat rsync/Dropbox tetap tidak bisa dijalankan
    # di Windows. Kalau keberadaan berkasnya saja yang diperiksa, preflight
    # lolos dan kegagalannya muncul jauh di dalam, per akun, dengan pesan
    # buram dari subprocess yang menolak jalan.
    pesan = rakit._galat_pemotong('win32', biner_ada=True)
    assert pesan is not None, \
        'berkas bernama potong dianggap cukup di mesin yang tak bisa menjalankannya'


@periksa('potong menghasilkan PNG beralfa dari gambar bersubjek')
def _():
    # Subjek disintesis di sini, bukan dimuat dari screenshot contoh di ss/ —
    # folder itu di-gitignore, jadi pemeriksaan yang bergantung padanya lulus
    # tanpa menegaskan apa pun di checkout mana pun selain satu mesin yang
    # kebetulan punya berkasnya secara lokal. Jangan kembalikan ke fixture.
    _butuh_potong()
    with tempfile.TemporaryDirectory() as t:
        from PIL import ImageDraw
        lebar, tinggi_kanvas = 800, 900
        asli = Path(t) / 'sosok.png'
        kanvas = Image.new('RGB', (lebar, tinggi_kanvas))
        gambar_ = ImageDraw.Draw(kanvas)
        for y in range(tinggi_kanvas):
            gambar_.line([(0, y), (lebar, y)], fill=(30 + y // 12, 40 + y // 15, 90 + y // 20))
        gambar_.ellipse([340, 120, 460, 240], fill=(240, 200, 170))
        gambar_.rounded_rectangle([320, 240, 480, 560], 40, fill=(200, 60, 60))
        gambar_.rounded_rectangle([355, 560, 405, 800], 20, fill=(40, 40, 70))
        gambar_.rounded_rectangle([405, 560, 455, 800], 20, fill=(40, 40, 70))
        kanvas.save(asli)

        keluar = Path(t) / 'potong.png'
        jalan = subprocess.run([str(POTONG), str(asli), str(keluar)],
                               capture_output=True, text=True)
        assert jalan.returncode == 0, jalan.stderr
        alfa = Image.open(keluar).convert('RGBA').getchannel('A')
        rendah, tinggi = alfa.getextrema()
        assert tinggi == 255, 'tidak ada piksel buram — tidak ada subjek yang terambil'
        assert rendah == 0, 'tidak ada piksel tembus — latar tidak terpotong sama sekali'


@periksa('potong menolak gambar tanpa subjek, bukan mengembalikan gambar utuh')
def _():
    _butuh_potong()
    with tempfile.TemporaryDirectory() as t:
        polos = Path(t) / 'polos.png'
        Image.new('RGB', (600, 600), (128, 128, 128)).save(polos)
        keluar = Path(t) / 'keluar.png'
        jalan = subprocess.run([str(POTONG), str(polos), str(keluar)],
                               capture_output=True, text=True)
        assert jalan.returncode != 0, 'gambar polos malah dianggap punya subjek'
        assert not keluar.exists(), 'berkas keluaran tetap ditulis padahal gagal'


import poster


@periksa('tata letak menapak satu garis dasar meski ukuran masukan jauh berbeda')
def _():
    # Angka nyata dari ss/: potongan datang 605px dan 1001px.
    #
    # CATATAN JUJUR (temuan review 8 Agu): assersi ini nyaris tautologis pada
    # bentuk poster.py SEKARANG — dasar dihitung SEKALI di luar loop lalu
    # y = dasar - tinggi untuk tiap karakter, jadi y + h == dasar berlaku
    # untuk tinggi APA PUN, benar atau salah. Cek ini tetap dipertahankan
    # (bukan dihapus) karena masih membatasi implementasi LAIN yang tidak
    # memakai bentuk shared-dasar ini (mis. yang menghitung dasar per
    # karakter dan salah membulatkannya) — tapi ia TIDAK BISA menangkap
    # pergeseran yang terjadi di tahap RENDER poster.rakit() (lihat cek di
    # bawah, yang membaca piksel poster sungguhan, bukan balikan fungsi ini).
    kotak = [(0, 0, 357, 605), (0, 0, 909, 1001), (0, 0, 400, 800)]
    tempat = poster.tata_letak((2000, 2500), kotak)
    dasar = [y + h for _, y, _, h in tempat]
    assert max(dasar) - min(dasar) <= 1, f'kaki tidak sejajar: {dasar}'


@periksa('bloom menyala dari benda terang-jenuh saja, tidak dari kulit atau kain abu')
def _():
    # Yang bikin senjata FF terbaca mewah adalah cahaya yang KELUAR dari
    # bendanya. Kalau ambangnya salah, kulit dan kain abu ikut menyala dan
    # kartunya terlihat berkabut, bukan mewah.
    def _petak(warna):
        im = Image.new('RGBA', (200, 200), (0, 0, 0, 0))
        ImageDraw.Draw(im).rectangle([40, 40, 160, 160], fill=warna + (255,))
        return im

    def _terang(im):
        titik = list(im.convert('L').getdata())
        return sum(titik) / len(titik)

    neon = _terang(poster._bloom(_petak((60, 255, 90))))     # hijau menyala
    kulit = _terang(poster._bloom(_petak((205, 170, 140))))  # kulit terang tapi pucat
    abu = _terang(poster._bloom(_petak((150, 150, 150))))    # abu netral

    assert neon > 8, f'benda neon tidak menyala sama sekali (rerata {neon:.1f})'
    assert kulit < neon / 4, \
        f'kulit ikut menyala hampir sekuat neon ({kulit:.1f} vs {neon:.1f})'
    assert abu < 1.0, f'abu netral ikut menyala ({abu:.1f}) — ambang kejenuhan bocor'


@periksa('bloom benar-benar hitam di luar cahaya, tidak melahirkan kotak persegi')
def _():
    # Cacat nyata 9 Agu: blur radius 55 menyebarkan nilai kecil (1-5 aras) ke
    # SELURUH persegi bloom. Nilai sekecil itu tak terlihat sendirian, tapi
    # ImageChops.screen mengangkat latar di dalam persegi dan tidak di luarnya,
    # sehingga batas perseginya terbaca sebagai kotak samar mengelilingi
    # karakter. Bloom yang tidak benar-benar nol di daerah gelap TIDAK boleh
    # lolos.
    # Ukurannya sebanding dengan produksi: kutout karakter datang sekitar
    # 1000x2000, jadi radius blur 55 di sana proporsional. Fixture mungil
    # membuat cahayanya menyebar habis dan ceknya merah karena alasan yang
    # salah.
    # Neonnya sengaja MENYENTUH tepi kutout — itulah keadaan nyatanya: senjata
    # karakter memang menjulur sampai batas kotak-batasnya. Fixture yang
    # menaruh sumber cahaya jauh dari tepi lolos tanpa membuktikan apa pun;
    # versi pertama cek ini melakukan itu dan hijau padahal kartunya berkotak.
    kutout = _kutout_uji((600, 900))
    pena = ImageDraw.Draw(kutout)
    pena.rectangle([500, 400, 599, 520], fill=(60, 255, 90, 255))
    cahaya = poster._bloom(kutout)

    assert cahaya.size == (600 + 2 * poster.BLOOM_TEPI, 900 + 2 * poster.BLOOM_TEPI), \
        (f'bloom {cahaya.size} tidak dilebihkan — cahaya akan terpotong di tepi '
         f'dan batasnya terbaca sebagai kotak')

    w, h = cahaya.size
    tepi = ([cahaya.getpixel((x, 0)) for x in range(0, w, 7)]
            + [cahaya.getpixel((x, h - 1)) for x in range(0, w, 7)]
            + [cahaya.getpixel((0, y)) for y in range(0, h, 7)]
            + [cahaya.getpixel((w - 1, y)) for y in range(0, h, 7)])
    bocor = [t for t in tepi if max(t) > 0]
    assert not bocor, \
        (f'{len(bocor)} titik di tepi bloom masih menyala (mis. {bocor[:3]}) — '
         f'ImageChops.screen akan mengangkat latar di dalam persegi saja, dan '
         f'batasnya terbaca sebagai kotak samar mengelilingi karakter')

    p = poster.BLOOM_TEPI
    assert max(cahaya.getpixel((p + 550, p + 460))) > 40, 'senjata neon tidak menyala sama sekali'


@periksa('rim light hanya di luar siluet, tidak menodai piksel karakter')
def _():
    kutout = _kutout_uji((160, 260))
    cincin = poster._rim_light(kutout)
    assert cincin.size == kutout.size, f'ukuran cincin {cincin.size}'

    dalam = kutout.getchannel('A').point(lambda v: 255 if v > 250 else 0)
    bocor = ImageChops.multiply(cincin.getchannel('A'), dalam)
    assert bocor.getextrema()[1] == 0, \
        'rim light menimpa bagian dalam siluet — ia harus jadi cahaya tepi, bukan kabut di badan'
    assert cincin.getchannel('A').getextrema()[1] > 40, \
        'cincin rim light nyaris tak terlihat'


@periksa('kartu yang melebihi batas unggah situs menghentikan proses, bukan diam-diam disimpan')
def _():
    # Situs jagotopup menolak unggahan di atas 5120 KB. Kartu yang melewati
    # batas itu tidak berguna sama sekali — dan menyimpannya diam-diam berarti
    # pemilik baru tahu saat mengunggah satu per satu, bukan saat merakit.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        a = _akun_contoh(akar)
        kartu = template.rakit_kartu_utama(a, Image.open(a.poster), ASET)
        keluar = akar / 'hasil.webp'

        asli = template.BATAS_UNGGAH_KB
        template.BATAS_UNGGAH_KB = 1        # batas mustahil, memaksa penjaganya bicara
        try:
            template.ekspor(kartu, keluar)
        except antrean.GalatFatal as e:
            assert 'KB' in str(e), f'pesan tidak menyebut ukurannya: {e}'
        else:
            raise AssertionError(
                'kartu melebihi batas malah disimpan diam-diam — pemilik baru '
                'tahu saat unggahannya ditolak situs')
        finally:
            template.BATAS_UNGGAH_KB = asli

        # Dengan batas yang sebenarnya, kartu normal harus lolos tanpa protes.
        template.ekspor(kartu, keluar)
        assert keluar.stat().st_size / 1024 < template.BATAS_UNGGAH_KB


@periksa('ekspor tidak membuang hasil upscaler, dan tidak membesarkan artwork template')
def _():
    # Ditemukan 9 Agu: kutout keluar dari upscaler setinggi ~2280px, digambar
    # di poster 1724px, lalu seluruh kartu dikecilkan ke lebar 1080 dan
    # tinggal 713px. Tiga per empat kerja upscaler dibuang di langkah
    # terakhir, tanpa satu pun cek berubah merah.
    #
    # Ambang 1200 kira-kira separuh tinggi kutout hasil upscale dari sumber
    # WhatsApp: di bawah itu, membayar 4x upscale tidak lagi terbayar.
    lebar_ekspor, tinggi_ekspor = template.EKSPOR
    lebar_kanvas, tinggi_kanvas = template.KANVAS

    assert lebar_ekspor * 5 == tinggi_ekspor * 4, \
        f'ekspor {template.EKSPOR} bukan 4:5 — kartunya akan berubah bentuk di situs'
    assert lebar_ekspor <= lebar_kanvas and tinggi_ekspor <= tinggi_kanvas, \
        (f'ekspor {template.EKSPOR} melebihi kanvas {template.KANVAS} — '
         f'artwork templatenya ikut dibesarkan, dan itu cuma menambah berkas '
         f'tanpa menambah detail')

    _, _, _, tinggi_jendela = template.JENDELA_UTAMA
    tinggi_karakter = (tinggi_jendela * poster.TINGGI_KARAKTER * poster.SKALA_TENGAH
                       * lebar_ekspor / lebar_kanvas)
    assert tinggi_karakter >= 1200, (
        f'karakter tengah cuma {tinggi_karakter:.0f}px di kartu ekspor — '
        f'hasil upscale dibuang di langkah terakhir')


@periksa('tata letak menyusut sendiri supaya ada celah latar antar karakter')
def _():
    # Poster rujukan pemilik punya celah api yang terlihat di antara ketiga
    # karakter. Punya kami tidak, dan sebabnya bukan posisi melainkan LEBAR:
    # pada 777 senjata naga karakter kanan menjulur mendatar 1071px, sehingga
    # total ketiganya 2598px di panggung 2353px — kelebihan 245px sebelum
    # celah apa pun. Ukuran dan celah bertukar, dan yang menentukan adalah
    # pose, yang berbeda tiap akun.
    #
    # Maka mesin menyusut SENDIRI seperlunya, per akun: yang posenya rapat
    # tetap besar, yang menjulur mengalah. Bukan satu angka global yang
    # dipaksa muat untuk kasus terburuk.
    kanvas = (2353, 2521)

    rapat = [(0, 0, 700, 2000)] * 3            # total 2100, muat dengan celah
    tempat = poster.tata_letak(kanvas, rapat)
    assert max(t for _, _, _, t in tempat) == round(
        kanvas[1] * poster.TINGGI_KARAKTER * poster.SKALA_TENGAH), \
        'pose rapat ikut disusutkan padahal sudah muat'

    lebar_rapat = [lb for _, _, lb, _ in tempat]
    lubang = [tempat[1][0] - (tempat[0][0] + lebar_rapat[0]),
              tempat[2][0] - (tempat[1][0] + lebar_rapat[1])]
    assert all(c > 0 for c in lubang), f'tidak ada celah antar karakter: {lubang}'

    menjulur = [(0, 0, 700, 2000), (0, 0, 700, 2000), (0, 0, 1400, 2000)]
    tempat2 = poster.tata_letak(kanvas, menjulur)
    lebar2 = [lb for _, _, lb, _ in tempat2]
    lubang2 = [tempat2[1][0] - (tempat2[0][0] + lebar2[0]),
               tempat2[2][0] - (tempat2[1][0] + lebar2[1])]
    assert all(c > 0 for c in lubang2), \
        f'pose menjulur tetap bertumpuk, tidak disusutkan: celah {lubang2}'
    assert max(t for _, _, _, t in tempat2) < max(t for _, _, _, t in tempat), \
        'pose menjulur tidak ikut mengecil padahal tidak muat'


@periksa('inti alfa mengabaikan jubah dan bilah tipis, badan padat terukur penuh')
def _():
    # Diukur pada FF-PELAJAR-6001 (14 Agu): kutout karakter kiri 514x551 —
    # rasio 0,93, hampir persegi — padahal badannya cuma 353px. Sisanya jubah
    # biru mengembang dan bilah sabit yang menjulur mendatar. Kotak-batas alfa
    # menghitung jubah itu seberat badan, jadi ketiga karakter disusutkan 38%
    # dan kartunya terbaca kerdil dengan 45% ruang kosong di atas kepala.
    #
    # Yang membedakan badan dari jubah bukan warna atau kepekatan, melainkan
    # CAKUPAN TEGAK: kolom badan terisi hampir setinggi karakter, kolom jubah
    # dan bilah cuma sepotong kecil.
    padat = Image.new('RGBA', (300, 900), (200, 30, 30, 255))
    assert poster.inti_alfa(padat) == (0, 300), \
        f'badan padat ikut terkikis: {poster.inti_alfa(padat)}'

    im = Image.new('RGBA', (1000, 900), (0, 0, 0, 0))
    pena = ImageDraw.Draw(im)
    pena.rectangle([700, 0, 999, 899], fill=(200, 30, 30, 255))   # badan, 300px
    pena.rectangle([0, 430, 699, 469], fill=(60, 120, 255, 255))  # bilah, 40px = 4% tinggi
    assert poster.inti_alfa(im) == (700, 1000), \
        f'bilah mendatar ikut terhitung sebagai badan: {poster.inti_alfa(im)}'


@periksa('gumpalan setinggi peliharaan tidak dihitung badan, walau pekat dan besar')
def _():
    # FF-REGULER-6001, 14 Agu: peliharaan menempel di bilah pedang karakter
    # tengah. Diukur, ia TIDAK bisa dipisahkan — erosi 12 piksel pun
    # meninggalkan badan, pedang, dan peliharaan sebagai satu komponen
    # tersambung, karena bilahnya memang masuk ke daerah peliharaan. Membuangnya
    # berarti memotong pedang, dan skin senjata itu barang yang dibayar pembeli.
    #
    # Jadi yang dilakukan bukan membuangnya, melainkan berhenti menghitungnya
    # sebagai badan — supaya orangnya yang dipusatkan, bukan orang + peliharaan.
    # Terukur di bahan itu: kolom peliharaan menutupi 12-24% tinggi, kolom badan
    # 37-74%. Pemisahannya lega, dan fixture ini duduk di tengah jurang itu.
    im = Image.new('RGBA', (1000, 900), (0, 0, 0, 0))
    pena = ImageDraw.Draw(im)
    pena.rectangle([0, 0, 299, 899], fill=(200, 30, 30, 255))       # badan, setinggi penuh
    pena.rectangle([600, 700, 999, 899], fill=(30, 160, 60, 255))   # peliharaan, 200px = 22%
    assert poster.inti_alfa(im) == (0, 300), \
        f'gumpalan peliharaan ikut terhitung badan: {poster.inti_alfa(im)}'


@periksa('yang menjulur dari karakter tengah jatuh di BELAKANG tetangganya')
def _():
    # Pasangan cek di atas. Berhenti menghitung peliharaan sebagai badan
    # membuat orangnya terpusat, tapi peliharaannya lalu menggantung ke wilayah
    # tetangga — dan di situ urutan tempel yang menentukan kartunya berantakan
    # atau tidak. Digambar terakhir, ia menutupi badan karakter kanan; digambar
    # duluan, ia mengintip dari belakangnya.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        _buat_akun(akar, 'premium', '9301', n_karakter=3)
        akun, dilewati = antrean.baca(akar)
        assert dilewati == [], dilewati

        # Merah vs biru, bukan nilai persis: kutout lewat _perlakukan_karakter,
        # rim light, dan bloom sebelum mendarat, jadi yang bisa diandalkan
        # kanal mana yang menang, bukan angkanya.
        def _potong_palsu(berkas, tujuan):
            if berkas.stem != '2':
                return Image.new('RGBA', (300, 900), (40, 90, 220, 255))
            im = Image.new('RGBA', (1000, 900), (0, 0, 0, 0))
            pena = ImageDraw.Draw(im)
            pena.rectangle([0, 0, 299, 899], fill=(200, 40, 40, 255))     # badan
            pena.rectangle([300, 700, 999, 899], fill=(200, 40, 40, 255)) # julurannya
            return im

        potong_asli, naikkan_asli = poster._potong, poster._naikkan_resolusi
        poster._potong = _potong_palsu
        poster._naikkan_resolusi = lambda im, tinggi_tayang: im
        try:
            with latar_sementara(Path(t) / 'latar', (2353, 2521), (20, 20, 20, 255)):
                hasil = poster.rakit(akun[0], Path(t) / 'aset')
        finally:
            poster._potong, poster._naikkan_resolusi = potong_asli, naikkan_asli

        kotak = [(0, 0, 300, 900), (0, 0, 1000, 900), (0, 0, 300, 900)]
        tempat = poster.tata_letak(hasil.size, kotak, [(0, 300)] * 3)
        x_kanan, y_kanan, lebar_kanan, tinggi_kanan = tempat[2]

        # Titik di dalam badan karakter kanan DAN di dalam juluran tengah.
        skala_tengah = tempat[1][2] / 1000
        juluran_kiri = tempat[1][0] + round(300 * skala_tengah)
        juluran_atas = tempat[1][1] + round(700 * skala_tengah)
        x = x_kanan + lebar_kanan // 2
        y = y_kanan + tinggi_kanan - 100
        assert x > juluran_kiri and y > juluran_atas, \
            f'fixture tidak menghasilkan tumpang tindih: titik ({x},{y})'

        merah, hijau, biru = hasil.getpixel((x, y))[:3]
        assert biru > merah, \
            (f'juluran karakter tengah menimpa badan karakter kanan di ({x},{y}): '
             f'RGB {(merah, hijau, biru)} — yang tengah harus ditempel DULU')


@periksa('penyusutan diukur dari inti badan, bukan dari jubah yang menjulur')
def _():
    # Pasangan cek di atas, pada tingkat tata letak: jubah boleh menyelinap di
    # belakang tetangganya, dan yang harus punya celah adalah BADANnya.
    kanvas = (2353, 2521)
    kotak = [(0, 0, 1400, 2000), (0, 0, 700, 2000), (0, 0, 700, 2000)]
    inti = [(700, 1400), (0, 700), (0, 700)]   # yang kiri: separuh lebarnya jubah

    penuh = poster.tata_letak(kanvas, kotak)
    ramping = poster.tata_letak(kanvas, kotak, inti)

    target = round(kanvas[1] * poster.TINGGI_KARAKTER * poster.SKALA_TENGAH)
    assert penuh[1][3] < target, 'fixture tidak menyusut sama sekali — cek ini tidak membuktikan apa pun'
    assert ramping[1][3] == target, \
        (f'karakter tetap disusutkan jadi {ramping[1][3]} dari {target} padahal '
         f'inti badannya sudah muat berikut celah')

    # Celah dijamin antar INTI, bukan antar kotak-batas.
    kiri_inti = [t[0] + round((inti[i][0] - kotak[i][0]) * t[2] / (kotak[i][2] - kotak[i][0]))
                 for i, t in enumerate(ramping)]
    lebar_inti = [round((inti[i][1] - inti[i][0]) * t[2] / (kotak[i][2] - kotak[i][0]))
                  for i, t in enumerate(ramping)]
    lubang = [kiri_inti[1] - (kiri_inti[0] + lebar_inti[0]),
              kiri_inti[2] - (kiri_inti[1] + lebar_inti[1])]
    assert all(c > 0 for c in lubang), f'badan masih bertumpuk: celah inti {lubang}'


@periksa('rakit() mengukur lebar dari inti, jadi jubah lebar tidak mengerdilkan kartu')
def _():
    # Cek di atas menguji aritmetikanya. Ini menguji bahwa JALUR PRODUKSI
    # sungguh memakainya — menghapus argumen inti dari poster.rakit tetap
    # hijau tanpa cek ini.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        _buat_akun(akar, 'premium', '9201', n_karakter=3)
        akun, dilewati = antrean.baca(akar)
        assert dilewati == [], dilewati

        def _potong_palsu(berkas, tujuan):
            im = Image.new('RGBA', (1000, 900), (0, 0, 0, 0))
            pena = ImageDraw.Draw(im)
            pena.rectangle([700, 0, 999, 899], fill=(200, 30, 30, 255))
            pena.rectangle([0, 430, 699, 469], fill=(60, 120, 255, 255))
            return im

        potong_asli, naikkan_asli = poster._potong, poster._naikkan_resolusi
        poster._potong = _potong_palsu
        # Diganti identitas: yang diuji tata letaknya, dan cek ini tidak boleh
        # menuntut biner GPU 27MB hadir.
        poster._naikkan_resolusi = lambda im, tinggi_tayang: im
        catat = []
        try:
            with latar_sementara(Path(t) / 'latar', (2353, 2521), (20, 20, 20, 255)):
                hasil = poster.rakit(akun[0], Path(t) / 'aset', catat)
        finally:
            poster._potong, poster._naikkan_resolusi = potong_asli, naikkan_asli

        target = hasil.height * poster.TINGGI_KARAKTER * poster.SKALA_TENGAH
        tempat = poster.tata_letak(hasil.size, [(0, 0, 1000, 900)] * 3,
                                   [(700, 1000)] * 3)
        assert tempat[1][3] >= target * 0.97, \
            (f'karakter tengah cuma {tempat[1][3]}px dari {target:.0f}px — bilah '
             f'mendatar masih ikut dihitung sebagai lebar badan')
        assert catat == [], f'peringatan menyusut menyala padahal badannya muat: {catat}'


@periksa('kepala karakter punya ruang napas, bukan sekadar muat')
def _():
    # "Muat" saja tidak cukup, dan itu terbukti: pada TINGGI_KARAKTER 0,81
    # dengan GARIS_DASAR 0,93 kepala secara aritmetika MUAT (ruang 0,7%), tapi
    # di kartu jadi ia mentok tepi jendela dan terbaca terpenggal. Pemilik
    # menolaknya begitu melihat.
    #
    # Ambang 8% diambil dari poster rujukan pemilik, yang ruang kepalanya
    # terukur ~13% tinggi jendela — cukup longgar untuk menerima variasi gaya,
    # cukup ketat untuk menolak 0,7%.
    ruang = poster.GARIS_DASAR - poster.TINGGI_KARAKTER * poster.SKALA_TENGAH
    assert ruang >= 0.08, (
        f'ruang di atas kepala cuma {ruang*100:.1f}% tinggi kanvas — kepala akan '
        f'terbaca mentok tepi jendela. Referensi punya ~13%.')


@periksa('kepala karakter muat di kanvas — tinggi tidak boleh melebihi garis dasar')
def _():
    # Cacat yang tidak pernah terjaga sampai 9 Agu: peringatan "terpotong tepi
    # poster" yang sudah ada hanya memeriksa kiri dan kanan, tidak pernah ATAS.
    # Karakter digambar dari garis dasar ke ATAS, jadi begitu tingginya
    # melebihi garis dasar, kepalanya terpenggal di tepi kanvas — diam-diam,
    # tanpa satu pun baris peringatan. Terukur saat menaikkan ukuran: pada
    # TINGGI_KARAKTER 0,78 dengan GARIS_DASAR 0,82, kepala karakter tengah
    # mendarat di y=-175.
    #
    # Yang tengah dipakai sebagai patokan karena ia yang tertinggi
    # (SKALA_TENGAH). Ini juga yang mengikat ukuran dengan garis dasar:
    # karakter besar MENSYARATKAN kaki turun, bukan sekadar boleh.
    puncak = poster.TINGGI_KARAKTER * poster.SKALA_TENGAH
    assert puncak <= poster.GARIS_DASAR, (
        f'karakter tengah setinggi {puncak:.3f} kanvas padahal garis dasarnya '
        f'{poster.GARIS_DASAR:.3f} — kepalanya terpenggal {puncak - poster.GARIS_DASAR:.3f} '
        f'kanvas di atas')


@periksa('poster memperingatkan kalau latar di belakang label terlalu terang untuk teks putih')
def _():
    # Menggantikan cek lama yang menuntut kaki berhenti DI ATAS pita label.
    # Premis cek itu keliru: template.rakit_kartu_utama menempel poster dulu
    # lalu meng-alpha_composite bingkainya DI ATAS, jadi tulisan label tidak
    # pernah bisa tertutup karakter. Yang benar-benar rusak pada 777 dulu
    # bukan tertutupnya tulisan, melainkan KONTRASnya: teks putih di atas
    # sepatu merah-putih yang ramai. Kaki gelap di belakang teks putih justru
    # terbaca bagus — dan cek lama akan melarangnya tanpa alasan.
    terang = Image.new('RGBA', (400, 400), (245, 245, 245, 255))
    gelap = Image.new('RGBA', (400, 400), (25, 25, 30, 255))
    assert poster._latar_label_terlalu_terang(terang), \
        'latar putih di belakang teks putih tidak diperingatkan'
    assert not poster._latar_label_terlalu_terang(gelap), \
        'latar gelap diperingatkan padahal teks putih justru terbaca jelas di atasnya'


@periksa('kaki ketiga karakter benar-benar sejajar pada POSTER YANG DIRAKIT, bukan cuma balikan tata_letak')
def _():
    # Menggantikan sumber slide cek di atas: bukan aritmetika tata_letak
    # (yang benar secara konstruksi untuk tinggi apa pun), tapi PIKSEL poster
    # yang sungguh ditempel lewat poster.rakit(). Ini akan merah pada bug
    # pembulatan, pergeseran per-karakter, atau refactor masa depan yang
    # meninggalkan bentuk shared-dasar — tak satu pun bisa dilihat cek lama.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        _buat_akun(akar, 'premium', '9003', n_karakter=3)
        akun, dilewati = antrean.baca(akar)
        assert dilewati == [], dilewati

        aset = Path(t) / 'aset'
        pass  # latar dipasang lewat latar_sementara di bawah
        ukuran_kanvas = (2000, 2500)
        # Latar sengaja TEMBUS (alfa 0), bukan opak: rona hangat penuh
        # kanvas di akhir rakit() bikin latar-yang-opak selalu beralfa 255
        # di mana-mana, jadi "baris beralfa penuh" tak bisa membedakan kaki
        # karakter dari latar kosong. Dengan latar tembus, alfa 255 CUMA
        # muncul di piksel karakter (dan bayangannya, yang alfanya di bawah
        # 255 sehingga tidak ikut tertangkap).
        ukuran_latar = ukuran_kanvas

        # Tiga ukuran sengaja BEDA — angka nyata dari ss/, sama seperti cek di atas.
        ukuran = [(357, 605), (909, 1001), (400, 800)]

        def _potong_palsu(berkas, tujuan):
            w, h = ukuran[int(berkas.stem) - 1]
            return Image.new('RGBA', (w, h), (200, 30, 30, 255))

        potong_asli = poster._potong
        poster._potong = _potong_palsu
        try:
            with latar_sementara(Path(t) / 'latar', ukuran_latar,
                                 (0, 0, 0, 0) if ukuran_latar == ukuran_kanvas else (10, 10, 10, 255)):
                hasil = poster.rakit(akun[0], aset)
        finally:
            poster._potong = potong_asli

        # tata_letak dipanggil ulang HANYA untuk tahu rentang-X tiap
        # karakter (ke kolom mana harus dipindai) — Y-nya sengaja diabaikan,
        # kaki sungguhan digali dari piksel di bawah.
        kotak_alfa = [(0, 0, w, h) for w, h in ukuran]
        tempat = poster.tata_letak(hasil.size, kotak_alfa)

        kaki = []
        for x, y, lebar, _ in tempat:
            kiri, kanan = x, x + lebar
            baris_kaki = None
            # Pindai dari BAWAH kanvas ke atas: baris beralfa-penuh pertama
            # yang ditemukan adalah baris terbawah tempat karakter itu
            # sungguh tertempel opak.
            for yy in range(hasil.size[1] - 1, -1, -1):
                if all(hasil.getpixel((xx, yy))[3] == 255 for xx in range(kiri, kanan)):
                    baris_kaki = yy
                    break
            assert baris_kaki is not None, \
                f'karakter di kolom {kiri}..{kanan} tidak punya baris beralfa penuh sama sekali'
            kaki.append(baris_kaki)

        assert max(kaki) - min(kaki) <= 1, f'kaki tidak sejajar pada poster sungguhan: {kaki}'


@periksa('tinggi ketiga karakter setara setelah dinormalkan')
def _():
    kotak = [(0, 0, 357, 605), (0, 0, 909, 1001), (0, 0, 400, 800)]
    tinggi = [h for _, _, _, h in poster.tata_letak((2000, 2500), kotak)]
    assert max(tinggi) / min(tinggi) < 1.25, f'tinggi timpang: {tinggi}'


@periksa('karakter tengah lebih besar dan berada di antara kiri dan kanan')
def _():
    # Nama diperjelas dari draf rencana: tes ini cuma menegaskan UKURAN dan
    # URUTAN-X hasil tata_letak — tata_letak tidak tahu apa-apa tentang urutan
    # gambar, dia cuma mengembalikan koordinat.
    #
    # Urutan tempelnya sendiri diuji lewat 'yang menjulur dari karakter tengah
    # jatuh di BELAKANG tetangganya'. Sejak 14 Agu yang tengah ditempel DULU,
    # dan besarnya datang dari SKALA_TENGAH — yang diperiksa baris di bawah —
    # bukan dari urutan itu.
    kotak = [(0, 0, 400, 800)] * 3
    tempat = poster.tata_letak((2000, 2500), kotak)
    assert tempat[1][3] > tempat[0][3], 'karakter tengah tidak lebih besar'
    assert tempat[0][0] < tempat[1][0] < tempat[2][0], 'urutan kiri-tengah-kanan salah'


@periksa('siluet karakter tidak pernah bertumpuk pada POSTER YANG DIRAKIT')
def _():
    # Menggantikan cek 'karakter tengah ditempel paling akhir'. Cek itu
    # mengambil sampel di titik irisan ketiga kotak untuk membuktikan yang
    # tengah menang. Irisan itu kini TIDAK ADA lagi: tata_letak menjamin celah
    # latar di antara ketiganya, jadi premis ceknya lenyap.
    #
    # Jaminan barunya lebih kuat dan itulah yang diuji di sini — bukan
    # aritmetika tata_letak, melainkan piksel poster yang benar-benar dirakit.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        _buat_akun(akar, 'premium', '5001', poster=False)
        akun, _ = antrean.baca(akar)
        aset = Path(t) / 'aset'
        shutil.copytree(ASET, aset)

        sisi = 1800
        warna = [(200, 30, 30, 255), (30, 200, 30, 255), (30, 30, 200, 255)]

        def _potong_palsu(berkas, tujuan):
            return Image.new('RGBA', (sisi, sisi), warna[int(berkas.stem) - 1])

        potong_asli = poster._potong
        poster._potong = _potong_palsu
        try:
            with latar_sementara(Path(t) / 'latar', (2353, 2521), (10, 10, 10, 255)):
                hasil = poster.rakit(akun[0], aset)
        finally:
            poster._potong = potong_asli

        tempat = poster.tata_letak(hasil.size, [(0, 0, sisi, sisi)] * 3)
        celah = [tempat[1][0] - (tempat[0][0] + tempat[0][2]),
                 tempat[2][0] - (tempat[1][0] + tempat[1][2])]
        assert all(c > 0 for c in celah), \
            f'karakter masih bertumpuk di poster yang dirakit: celah {celah}'

        # Celahnya harus benar-benar memperlihatkan LATAR, bukan sekadar tidak
        # bertumpuk secara aritmetika.
        x = tempat[0][0] + tempat[0][2] + celah[0] // 2
        y = tempat[1][1] + tempat[1][3] // 2
        piksel = hasil.getpixel((x, y))
        assert max(piksel[:3]) < 90, \
            f'celah antar karakter tidak memperlihatkan latar gelap: {piksel}'


# Lebar TETAP (bukan diturunkan dari poster.KIKIS_PIKSEL) yang mewakili fitur
# tersempit yang masih harus selamat dari erosi — laras senjata. Kalau ini
# dihitung dari K (mis. 2K+1), menaikkan K ikut melebarkan garisnya sendiri —
# tesnya lolos terus berapa pun K dinaikkan, persis risiko yang mau dicegah.
# Diukur 8 Agu: pada K=2 laras 5px ini SELAMAT (alfa maks 255); pada K=12
# laras yang SAMA HABIS TOTAL (alfa maks 0). 5px sendiri lebih sempit dari
# laras sungguhan pada resolusi lobi 2868x1320 — kalau yang ini mati, detail
# senjata asli sudah lebih dulu mati.
LEBAR_LARAS_UJI = 5


@periksa('_kikis_pinggiran mengikis alfa persis KIKIS_PIKSEL dari tiap sisi, tanpa menghabiskan fitur tipis')
def _():
    # Temuan review 8 Agu: kedua cek rakit() di atas menjembatani poster._potong
    # UTUH, jadi _kikis_pinggiran tidak pernah tereksekusi lewat cek mana pun.
    # Cek ini memanggilnya LANGSUNG pada gambar RGBA sintetis — satu-satunya
    # cara kontraknya sungguh diuji.
    from PIL import ImageDraw
    K = poster.KIKIS_PIKSEL
    margin = K + 10  # jauh dari tepi kanvas supaya perluasan-tepi filter tidak ikut terukur

    # Separuh pertama kontrak: blok opak solid kehilangan PERSIS K piksel per sisi.
    sisi = 100
    blok = Image.new('RGBA', (sisi + 2 * margin, sisi + 2 * margin), (0, 0, 0, 0))
    ImageDraw.Draw(blok).rectangle(
        [margin, margin, margin + sisi - 1, margin + sisi - 1], fill=(200, 50, 50, 255))
    bbox_awal = blok.getchannel('A').getbbox()
    bbox_akhir = poster._kikis_pinggiran(blok).getchannel('A').getbbox()
    diharapkan = (bbox_awal[0] + K, bbox_awal[1] + K, bbox_awal[2] - K, bbox_awal[3] - K)
    assert bbox_akhir == diharapkan, \
        f'blok solid tidak kehilangan persis {K}px per sisi: {bbox_awal} -> {bbox_akhir}'

    # Separuh kedua: fitur tipis TIDAK BOLEH habis total — ini yang mencegah
    # KIKIS_PIKSEL dinaikkan sampai laras senjata atau helai rambut ikut hilang.
    # Lebar garisnya SENGAJA TETAP (LEBAR_LARAS_UJI), bukan diturunkan dari K —
    # lihat komentar di konstantanya untuk kenapa itu wajib.
    tinggi_garis = 100
    garis = Image.new('RGBA', (LEBAR_LARAS_UJI + 2 * margin, tinggi_garis + 2 * margin), (0, 0, 0, 0))
    ImageDraw.Draw(garis).rectangle(
        [margin, margin, margin + LEBAR_LARAS_UJI - 1, margin + tinggi_garis - 1], fill=(255, 255, 255, 255))
    sisa = poster._kikis_pinggiran(garis).getchannel('A').getextrema()
    assert sisa[1] > 0, \
        (f'fitur tipis ({LEBAR_LARAS_UJI}px, lebar tetap yang mewakili laras senjata) '
         f'habis total oleh erosi (KIKIS_PIKSEL={K}) — erosi sudah kelewat dalam: {sisa}')


@periksa('_potong sungguh memanggil _kikis_pinggiran, bukan cuma bungkus subprocess kosong')
def _():
    # Melengkapi cek di atas: cek itu membuktikan KONTRAK _kikis_pinggiran
    # benar kalau dipanggil, tapi tidak membuktikan _potong() SUNGGUH
    # memanggilnya. subprocess.run dijembatani (bukan biner potong
    # sungguhan) supaya cek ini tidak butuh Vision — yang diuji di sini
    # cuma jalur pengikisan di dalam _potong, bukan deteksi subjek.
    from PIL import ImageDraw

    class _SuksesPalsu:
        returncode = 0
        stderr = ''

    def _subprocess_palsu(*a, **kw):
        return _SuksesPalsu()

    with tempfile.TemporaryDirectory() as t:
        tujuan = Path(t) / 'keluar.png'
        K = poster.KIKIS_PIKSEL
        margin = K + 10
        sisi = 100
        blok = Image.new('RGBA', (sisi + 2 * margin, sisi + 2 * margin), (0, 0, 0, 0))
        ImageDraw.Draw(blok).rectangle(
            [margin, margin, margin + sisi - 1, margin + sisi - 1], fill=(200, 50, 50, 255))
        blok.save(tujuan)   # simulasikan keluaran biner potong: sudah tertulis sebelum subprocess "jalan"
        bbox_awal = blok.getchannel('A').getbbox()

        subprocess_asli = poster.subprocess.run
        poster.subprocess.run = _subprocess_palsu
        try:
            hasil = poster._potong(Path(t) / 'masuk.png', tujuan)
        finally:
            poster.subprocess.run = subprocess_asli

        bbox_akhir = hasil.getchannel('A').getbbox()
        diharapkan = (bbox_awal[0] + K, bbox_awal[1] + K, bbox_awal[2] - K, bbox_awal[3] - K)
        assert bbox_akhir == diharapkan, \
            (f'_potong tidak mengikis pinggiran sama sekali — kemungkinan panggilan '
             f'_kikis_pinggiran hilang dari _potong: {bbox_awal} -> {bbox_akhir}')


@periksa('latar tingkat yang hilang menghentikan, bukan menghasilkan poster tanpa latar')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        _buat_akun(akar, 'premium', '5001')
        akun, _ = antrean.baca(akar)
        kosong = Path(t) / 'aset-tanpa-latar'
        kosong.mkdir(parents=True, exist_ok=True)
        try:
            with latar_sementara(Path(t) / 'latar-kosong', tingkat=()):
                poster.rakit(akun[0], kosong)
        except FileNotFoundError as e:
            # 'premium' saja tidak cukup: nama berkasnya sendiri adalah
            # "premium.png", jadi FileNotFoundError MENTAH dari Image.open
            # (kalau guard-nya dihapus) juga akan menyebut "premium" secara
            # kebetulan lewat path-nya — diverifikasi lewat mutasi (guard
            # dihapus, tes ini tetap hijau sebelum baris 'tingkat' ini
            # ditambahkan). Kata "tingkat" cuma ada di pesan guard buatan
            # sendiri, tidak pernah muncul di pesan OSError bawaan Python.
            assert 'premium' in str(e), f'pesan tidak menyebut tingkatnya: {e}'
            assert 'tingkat' in str(e).lower(), \
                (f'pesan cuma menyebut nama berkas secara kebetulan, bukan pesan guard '
                 f'yang sengaja ditulis — kemungkinan guard-nya hilang: {e}')
        else:
            raise AssertionError('latar hilang malah dilewati diam-diam')


def _energi_tepi(im):
    """Rerata magnitudo tepi. Tepi kanvas dibuang karena FIND_EDGES selalu
    melahirkan bingkai palsu di sana yang menenggelamkan beda yang diukur."""
    abu = im.convert('L').filter(ImageFilter.FIND_EDGES)
    dalam = abu.crop((2, 2, abu.width - 2, abu.height - 2))
    titik = list(dalam.getdata())
    return sum(titik) / len(titik)


def _latar_uji(ukuran=(400, 400)):
    """Gambar bergaris tajam — mewakili latar foto yang detailnya kaya."""
    im = Image.new('RGBA', ukuran, (200, 190, 170, 255))
    pena = ImageDraw.Draw(im)
    for x in range(0, ukuran[0], 8):
        pena.line([(x, 0), (x, ukuran[1])], fill=(40, 60, 40, 255), width=3)
    return im


@periksa('perlakuan latar menurunkan energi tepi — latar benar-benar mundur')
def _():
    asal = _latar_uji()
    hasil = poster._perlakukan_latar(asal)
    assert hasil.size == asal.size, f'ukuran latar berubah jadi {hasil.size}'
    sebelum, sesudah = _energi_tepi(asal), _energi_tepi(hasil)
    assert sesudah < sebelum * 0.6, \
        f'energi tepi cuma turun dari {sebelum:.1f} ke {sesudah:.1f} — latar belum mundur'


@periksa('perlakuan latar meredupkan mendekati LATAR_REDUP, tidak lebih gelap diam-diam')
def _():
    asal = _latar_uji()
    hasil = poster._perlakukan_latar(asal)

    def _rerata(im):
        titik = list(im.convert('L').getdata())
        return sum(titik) / len(titik)

    nisbah = _rerata(hasil) / _rerata(asal)
    assert abs(nisbah - poster.LATAR_REDUP) < 0.04, \
        f'kecerahan jadi {nisbah:.3f}x, padahal LATAR_REDUP={poster.LATAR_REDUP}'


def _kutout_uji(ukuran=(160, 260)):
    """Siluet beralfa dengan tekstur garis di dalamnya — mewakili kutout karakter."""
    im = Image.new('RGBA', ukuran, (0, 0, 0, 0))
    pena = ImageDraw.Draw(im)
    pena.ellipse([12, 12, ukuran[0] - 12, ukuran[1] - 12], fill=(92, 92, 110, 255))
    for y in range(30, ukuran[1] - 30, 7):
        pena.line([(20, y), (ukuran[0] - 20, y)], fill=(138, 128, 118, 255))
    return im


@periksa('perlakuan karakter menaikkan energi tepi — karakter benar-benar maju')
def _():
    asal = _kutout_uji()
    hasil = poster._perlakukan_karakter(asal)
    assert hasil.size == asal.size, f'ukuran kutout berubah jadi {hasil.size}'
    sebelum, sesudah = _energi_tepi(asal), _energi_tepi(hasil)
    assert sesudah > sebelum * 1.15, \
        f'energi tepi cuma naik dari {sebelum:.1f} ke {sesudah:.1f} — belum menggigit'


@periksa('perlakuan karakter tidak menyentuh kanal alfa sama sekali')
def _():
    asal = _kutout_uji()
    hasil = poster._perlakukan_karakter(asal)
    assert list(hasil.getchannel('A').getdata()) == list(asal.getchannel('A').getdata()), \
        ('alfa ikut berubah — tepinya akan melahirkan halo, persis cacat yang '
         'KIKIS_PIKSEL sudah susah payah buang')


@periksa('perlakuan karakter menaikkan saturasi, bukan cuma mempertajam')
def _():
    # Temuan review (minor): versi lama membandingkan hasil dengan ASAL, jadi
    # ia tetap hijau kalau baris ImageEnhance.Color dihapus — KONTRAS sendiri
    # sudah melebarkan selisih kanal, dan cek ini menagihnya sebagai bukti
    # saturasi. Pembandingnya kini rantai yang SAMA PERSIS dengan SATURASI
    # dinetralkan ke 1,0, jadi satu-satunya beda antara keduanya adalah
    # langkah saturasi itu sendiri. Kalau langkahnya hilang, rasionya jadi
    # TEPAT 1,00.
    asal = _kutout_uji()
    hasil = poster._perlakukan_karakter(asal)

    saturasi_asli = poster.SATURASI
    poster.SATURASI = 1.0
    try:
        netral = poster._perlakukan_karakter(asal)
    finally:
        poster.SATURASI = saturasi_asli

    def _rentang_warna(im):
        # Selisih kanal per piksel = ukuran kasar seberapa berwarna gambarnya.
        r, g, b = (list(im.convert('RGB').getchannel(k).getdata()) for k in range(3))
        return sum(max(a, c, d) - min(a, c, d) for a, c, d in zip(r, g, b)) / len(r)

    rasio = _rentang_warna(hasil) / _rentang_warna(netral)
    assert rasio > 1.0 + (poster.SATURASI - 1.0) * 0.5, \
        (f'rentang warna cuma {rasio:.3f}x dari rantai yang sama tanpa saturasi — '
         f'1,00 berarti ImageEnhance.Color tidak pernah dijalankan dan yang '
         f'terukur selama ini cuma efek samping KONTRAS')
    # ImageEnhance.Color memadu terhadap abu-abunya sendiri, jadi rentang kanal
    # menskala hampir lurus dengan faktornya — terukur 0,97..0,99 kali faktor
    # pada rentang 1,05..2,0. Toleransinya dibuat sebanding dengan konstanta,
    # bukan angka tetap, supaya cek ini tetap sah kalau pemilik menyetel
    # SATURASI, tapi tetap merah kalau faktornya dipaku terpisah dari
    # konstantanya.
    assert abs(rasio - poster.SATURASI) < poster.SATURASI * 0.08, \
        (f'saturasi terukur {rasio:.3f}x, padahal SATURASI={poster.SATURASI} — '
         f'faktor yang dipakai bukan konstanta itu')


@periksa('arsip upscaler bersidik jari salah ditolak, tidak diekstrak, tidak dijalankan')
def _():
    with tempfile.TemporaryDirectory() as t:
        palsu = Path(t) / 'palsu.zip'
        palsu.write_bytes(b'ini bukan arsip Real-ESRGAN')
        try:
            poster._periksa_sidik(palsu)
        except antrean.GalatFatal as e:
            pesan = str(e)
            assert poster.UPSCALE_SHA256 in pesan, \
                'pesan tidak menyebut sidik jari yang diharapkan, jadi tidak bisa ditelusuri'
            assert 'tidak dijalankan' in pesan, \
                'pesan tidak menegaskan bahwa berkasnya tidak dieksekusi'
        else:
            raise AssertionError('arsip palsu malah diterima — ini lubang keamanan')


@periksa('sidik jari yang cocok diterima tanpa protes')
def _():
    with tempfile.TemporaryDirectory() as t:
        isi = b'apa pun'
        berkas = Path(t) / 'a.bin'
        berkas.write_bytes(isi)
        asli = poster.UPSCALE_SHA256
        poster.UPSCALE_SHA256 = hashlib.sha256(isi).hexdigest()
        try:
            poster._periksa_sidik(berkas)   # tidak boleh melempar
        finally:
            poster.UPSCALE_SHA256 = asli


def _arsip_upscaler_palsu(folder, nama=('upscaler-palsu.zip',)):
    """Zip tiruan sebentuk arsip Real-ESRGAN: tiga anggota yang dipatok + sisanya.

    Dibangun di sini, bukan mengunduh yang asli 52MB: cek yang bergantung pada
    jaringan akan merah karena alasan yang tidak ada hubungannya, dan cek yang
    bergantung pada berkas yang kebetulan sudah ada di satu mesin akan hijau
    tanpa memeriksa apa pun di mesin lain. Yang diuji adalah URUTAN dan
    PEMILIHAN anggota — dua sifat yang tidak peduli isi berkasnya sungguhan.
    """
    arsip = Path(folder) / nama[0]
    with zipfile.ZipFile(arsip, 'w') as z:
        for anggota in poster._ANGGOTA:
            z.writestr(anggota, f'isi tiruan untuk {anggota}'.encode())
        # Sisa arsip aslinya: sembilan model lain plus berkas pelengkap —
        # 50MB yang tidak pernah dibuka, dan tidak boleh mendarat di disk.
        for i in range(1, 10):
            z.writestr(f'models/model-lain-{i}-x4.bin', b'model yang tidak dipakai')
            z.writestr(f'models/model-lain-{i}-x4.param', b'param yang tidak dipakai')
        z.writestr('README.md', b'dokumen yang tidak dipakai')
        z.writestr('input.jpg', b'contoh yang tidak dipakai')
    return arsip


def _isi_folder(folder):
    """Daftar jalur relatif SEMUA berkas di bawah folder, terurut."""
    folder = Path(folder)
    if not folder.exists():
        return []
    return sorted(p.relative_to(folder).as_posix()
                  for p in folder.rglob('*') if p.is_file())


@periksa('arsip bersidik jari salah tidak menyisakan SATU berkas pun di folder upscaler')
def _():
    # Temuan review C2. Cek sidik jari yang sudah ada memanggil _periksa_sidik
    # LANGSUNG, jadi ia tidak tahu apa-apa soal kapan pemeriksaan itu terjadi
    # relatif terhadap ekstraksi. Memindahkan _periksa_sidik(arsip) ke BAWAH
    # loop ekstraksi tetap hijau — padahal itu berarti biner tak dikenal sudah
    # mendarat di disk, sudah di-chmod 0755, dan karantinanya sudah dilepas
    # sebelum ada yang memeriksa asal-usulnya. Ini sifat paling berisiko di
    # seluruh rancangan, jadi ia harus diuji ujung-ke-ujung.
    #
    # Arsipnya disajikan lewat file:// ke berkas sementara: _ambil_upscaler
    # dijalankan UTUH (unduh, periksa, ekstrak) tanpa menyentuh jaringan.
    with tempfile.TemporaryDirectory() as t:
        arsip = _arsip_upscaler_palsu(t)
        tujuan = Path(t) / 'upscaler'
        asli_url, asli_dir = poster.UPSCALE_URL, poster.UPSCALE_DIR
        poster.UPSCALE_URL = arsip.as_uri()
        poster.UPSCALE_DIR = tujuan
        try:
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    poster._ambil_upscaler()
            except antrean.GalatFatal as e:
                assert 'sidik jari' in str(e), \
                    f'berhenti karena sebab lain, bukan sidik jari: {e}'
            else:
                raise AssertionError(
                    'arsip bersidik jari salah malah diterima sampai selesai')
        finally:
            poster.UPSCALE_URL, poster.UPSCALE_DIR = asli_url, asli_dir

        sisa = _isi_folder(tujuan)
        assert sisa == [], \
            (f'arsip yang ditolak tetap meninggalkan berkas di disk: {sisa}. '
             f'Sidik jari diperiksa SESUDAH ekstraksi — biner tak dikenal sudah '
             f'mendarat sebelum ada yang tahu asal-usulnya.')


class _upscaler_dari_arsip:
    """Arahkan _ambil_upscaler ke arsip tiruan lokal selama satu cek.

    Sidik jari yang dipatok ikut ditimpa dengan sha256 arsip tiruan itu supaya
    alurnya menembus sampai ekstraksi — yang diuji cek-cek pemakainya adalah
    apa yang terjadi SESUDAH sidik jari cocok. Ketiganya dikembalikan di
    __exit__ supaya tidak ada yang bocor ke cek berikutnya.
    """

    def __init__(self, arsip, tujuan):
        self.arsip, self.tujuan = Path(arsip), Path(tujuan)

    def __enter__(self):
        self.asli = (poster.UPSCALE_URL, poster.UPSCALE_DIR, poster.UPSCALE_SHA256)
        poster.UPSCALE_URL = self.arsip.as_uri()
        poster.UPSCALE_DIR = self.tujuan
        poster.UPSCALE_SHA256 = hashlib.sha256(self.arsip.read_bytes()).hexdigest()
        return self.tujuan

    def __exit__(self, *a):
        poster.UPSCALE_URL, poster.UPSCALE_DIR, poster.UPSCALE_SHA256 = self.asli
        return False


@periksa('xattr yang gagal MENGHENTIKAN, dan penanda .siap tidak pernah ditulis')
def _():
    # Temuan review I4. Balikan xattr dulu diabaikan: kalau ia gagal, karantina
    # tetap menempel, "upscaler siap" tetap tercetak, dan .siap menyatakan
    # SELAMANYA bahwa folder itu beres. Sesudahnya tiap lari pulang lewat
    # cabang cache-hit dan gagal per akun dengan pesan buram dari biner yang
    # ditolak macOS — tanpa pernah mencoba melepas karantinanya lagi.
    with tempfile.TemporaryDirectory() as t:
        arsip = _arsip_upscaler_palsu(t)

        class _XattrGagal:
            returncode = 1
            stdout = ''
            stderr = 'xattr: [Errno 1] Operation not permitted'

        subprocess_asli = poster.subprocess.run
        poster.subprocess.run = lambda *a, **kw: _XattrGagal()
        try:
            with _upscaler_dari_arsip(arsip, Path(t) / 'upscaler') as tujuan:
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        poster._ambil_upscaler()
                except antrean.GalatFatal as e:
                    assert 'xattr' in str(e), \
                        f'berhenti karena sebab lain, bukan karantina: {e}'
                    assert 'com.apple.quarantine' in str(e), \
                        f'pesan tidak memberi perintah yang bisa dijalankan sendiri: {e}'
                else:
                    raise AssertionError(
                        'xattr gagal malah dianggap sukses — folder yang binernya '
                        'ditolak macOS lolos sebagai siap')
        finally:
            poster.subprocess.run = subprocess_asli

        assert poster._PENANDA_SIAP not in _isi_folder(tujuan), \
            (f'penanda {poster._PENANDA_SIAP} tetap ditulis padahal karantina belum '
             f'lepas — folder cacat itu kini bersertifikat siap selamanya dan lari '
             f'berikutnya tidak akan pernah mencoba ulang')


@periksa('cuma tiga anggota yang dipatok yang diekstrak; sembilan model lain tidak menyentuh disk')
def _():
    # Uji 13 rancangan, yang belum pernah ditulis: tidak ada cek satu pun yang
    # menyebut _ANGGOTA. Kalau loop selektifnya diganti z.extractall(), 50MB
    # berkas yang tidak pernah dibuka mendarat di disk pemilik tanpa ada yang
    # tahu — dan setiap berkas dari arsip yang diekstrak adalah permukaan
    # tambahan pada arsip yang isinya memang akan dieksekusi.
    with tempfile.TemporaryDirectory() as t:
        arsip = _arsip_upscaler_palsu(t)
        with _upscaler_dari_arsip(arsip, Path(t) / 'upscaler') as tujuan:
            with contextlib.redirect_stdout(io.StringIO()):
                poster._ambil_upscaler()

        di_disk = _isi_folder(tujuan)
        diharapkan = sorted(list(poster._ANGGOTA) + [poster._PENANDA_SIAP])
        assert di_disk == diharapkan, \
            f'isi folder upscaler tidak persis anggota yang dipatok: {di_disk}'

        # Ditegaskan sekali lagi secara eksplisit terhadap ISI ARSIP, bukan
        # cuma terhadap daftar harapan di atas: kalau _ANGGOTA suatu saat
        # ikut dilebarkan, assersi kesamaan di atas ikut melebar bersamanya
        # dan berhenti menjaga apa pun. Yang ini tidak bisa ikut bergeser.
        with zipfile.ZipFile(arsip) as z:
            semua = [n for n in z.namelist() if not n.endswith('/')]
        tidak_dipakai = [n for n in semua if n not in poster._ANGGOTA]
        assert tidak_dipakai, 'prasyarat: arsip tiruan harus punya anggota yang tidak dipakai'
        for nama in tidak_dipakai:
            assert not (tujuan / nama).exists(), \
                f'anggota arsip yang tidak dipatok ikut diekstrak: {nama}'


@periksa('unduhan gagal BERHENTI menyebut sebabnya, tidak mundur diam-diam')
def _():
    asli_url = poster.UPSCALE_URL
    asli_dir = poster.UPSCALE_DIR
    with tempfile.TemporaryDirectory() as t:
        poster.UPSCALE_URL = 'https://127.0.0.1:1/tidak-ada.zip'
        poster.UPSCALE_DIR = Path(t) / 'upscaler'
        try:
            poster._ambil_upscaler()
        except antrean.GalatFatal as e:
            assert 'jaringan' in str(e) or 'unduhan' in str(e), \
                f'pesan tidak menjelaskan bahwa sebabnya unduhan: {e}'
        else:
            raise AssertionError(
                'unduhan gagal malah lolos — mesin akan menghasilkan kartu '
                'yang dikira sudah HD padahal tidak')
        finally:
            poster.UPSCALE_URL = asli_url
            poster.UPSCALE_DIR = asli_dir


@periksa('unduhan upscaler yang gagal MENGHENTIKAN seluruh antrean, bukan jadi N baris DILEWATI')
def _():
    # Temuan review I3. Jaringan mati saat lari 30 akun tanpa pengawas dulu
    # menghasilkan 30 baris DILEWATI identik dan exit 0 — tak terbedakan dari
    # 30 folder yang memang rusak sendiri-sendiri, dan pemilik menghabiskan
    # paginya membuka folder yang sebenarnya sehat. Aturannya sudah tertulis
    # di rakit.py (komentar preflight Perkakas B) dengan biner potong sebagai
    # preseden; pengambilan upscaler cuma belum mengikutinya.
    #
    # Dua akun sengaja, bukan satu: yang dijaga di sini justru sifat "berhenti
    # di akun PERTAMA", jadi satu akun saja tidak bisa membedakan berhenti
    # dari dilewati-lalu-habis.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        _buat_akun(akar, 'premium', '5001', n_karakter=3, poster=False)
        _buat_akun(akar, 'reguler', '5002', n_karakter=3, poster=False)

        asli_url, asli_dir = poster.UPSCALE_URL, poster.UPSCALE_DIR
        potong_asli = poster._potong
        poster.UPSCALE_URL = 'https://127.0.0.1:1/tidak-ada.zip'
        poster.UPSCALE_DIR = Path(t) / 'upscaler-kosong'
        # Kutout sengaja KECIL supaya penjaga pelewatan _naikkan_resolusi tidak
        # menyelamatkannya — jalur unduhan harus sungguh tersentuh.
        poster._potong = lambda berkas, tujuan_: Image.new('RGBA', (226, 570), (180, 90, 60, 255))
        try:
            with latar_sementara(Path(t) / 'latar', (2353, 2521), (20, 20, 20, 255),
                                 tingkat=('premium', 'reguler')):
                dibuat, dilewati, _, _ = rakit.jalankan(akar, tujuan, ASET)
        except antrean.GalatFatal as e:
            assert 'unduhan' in str(e) or 'jaringan' in str(e), \
                f'berhenti tanpa menyebut bahwa sebabnya unduhan upscaler: {e}'
        else:
            raise AssertionError(
                f'jaringan mati malah dilaporkan sebagai cacat per-folder dengan exit 0: '
                f'dibuat={dibuat} dilewati={dilewati}')
        finally:
            poster.UPSCALE_URL, poster.UPSCALE_DIR = asli_url, asli_dir
            poster._potong = potong_asli


@periksa('folder upscaler setengah jadi (biner + .bin tanpa .param) tidak dianggap cache sah')
def _():
    # Ekstraksi menulis tiap anggota langsung ke path final — kalau lari
    # sebelumnya terputus setelah biner dan .bin tertulis tapi sebelum
    # .param (atau sebelum chmod/xattr), sisa di disk itu tidak boleh lolos
    # sebagai "siap". URL dipaksa ke alamat yang gagal: kalau folder
    # setengah jadi ini SALAH dianggap cache sah, _ambil_upscaler() akan
    # balik tanpa menyentuh jaringan sama sekali dan tidak ada RuntimeError
    # — persis cabang yang harus digagalkan tes ini.
    asli_url = poster.UPSCALE_URL
    asli_dir = poster.UPSCALE_DIR
    with tempfile.TemporaryDirectory() as t:
        upscaler_dir = Path(t) / 'upscaler'
        model_dir = upscaler_dir / 'models'
        model_dir.mkdir(parents=True)
        (upscaler_dir / 'realesrgan-ncnn-vulkan').write_bytes(b'biner dari lari yang terputus')
        (model_dir / f'{poster.UPSCALE_BERKAS}.bin').write_bytes(b'model palsu')
        # .param sengaja tidak ditulis — mensimulasikan lari yang terputus di tengah.

        poster.UPSCALE_URL = 'https://127.0.0.1:1/tidak-ada.zip'
        poster.UPSCALE_DIR = upscaler_dir
        try:
            try:
                poster._ambil_upscaler()
            except antrean.GalatFatal:
                pass  # diharapkan: folder dianggap belum siap, coba unduh ulang, gagal (jaringan palsu)
            else:
                raise AssertionError(
                    'folder setengah jadi (tanpa .param) malah dianggap cache sah — '
                    'tidak pernah mencoba mengunduh ulang')
        finally:
            poster.UPSCALE_URL = asli_url
            poster.UPSCALE_DIR = asli_dir


def _butuh_upscaler():
    """Lewati cek ini kalau binernya belum pernah diunduh di mesin ini."""
    biner = poster.UPSCALE_DIR / 'realesrgan-ncnn-vulkan'
    if not biner.exists():
        raise Lewat('biner upscaler belum diunduh; jalankan perakit sekali dulu')


@periksa('kutout kecil naik 4x dan porsi alfa separuh-tembus tidak melonjak')
def _():
    _butuh_upscaler()
    asal = _kutout_uji((226, 570))
    hasil = poster._naikkan_resolusi(asal, 1724)
    assert hasil.size == (904, 2280), f'ukuran keluaran {hasil.size}, bukan 4x'
    assert hasil.mode == 'RGBA', f'mode keluaran {hasil.mode}, alfa hilang'

    # Fixture ini beralfa keras (PIL menggambar tanpa antialias), jadi porsi
    # transisi di sumbernya nol dan rasio tak terdefinisi. Yang dijaga di sini
    # adalah pita transisi hasil upscale tetap TIPIS: interpolasi 4x pada tepi
    # keras memang melahirkan pita beberapa piksel, tapi upscaler yang mengaburkan
    # alfa akan membengkakkannya jauh melewati ambang ini.
    h = hasil.getchannel('A').histogram()
    porsi = sum(h[8:248]) / sum(h)
    assert porsi < 0.10, \
        f'pita alfa separuh-tembus {porsi:.1%} — tepinya kabur dan akan lahir jadi halo'


@periksa('upscaler deterministik: masukan sama menghasilkan piksel sama persis')
def _():
    _butuh_upscaler()
    asal = _kutout_uji((120, 300))
    a = poster._naikkan_resolusi(asal, 9999)
    b = poster._naikkan_resolusi(asal, 9999)
    assert a.tobytes() == b.tobytes(), \
        'dua lari atas masukan sama berbeda pikselnya — cek lain tidak bisa menuntut kesamaan'


@periksa('kutout yang sudah setinggi tayang dilewati, binernya tidak dipanggil')
def _():
    asal = _kutout_uji((300, 900))
    tinggi_alfa = asal.getchannel('A').getbbox()[3] - asal.getchannel('A').getbbox()[1]
    hasil = poster._naikkan_resolusi(asal, tinggi_alfa - 1)
    assert hasil is asal, \
        ('kutout yang sudah cukup besar tetap di-upscale — 4,28 detik dan 131MB '
         'untuk 32,7 megapiksel yang seluruhnya dibuang lagi')


@periksa('keluaran upscaler BUKAN LANCZOS 4x — mundur diam-diam ke resize biasa ketahuan')
def _():
    # Temuan review C1. Ketiga cek upscaler di atas (ukuran, mode, pita alfa,
    # determinisme) semuanya juga dipenuhi oleh `im.resize(4x, LANCZOS)` —
    # persis jalan mundur diam-diam yang dilarang rancangan (poin 12). Diukur
    # 8 Agu pada fixture ini: rerata selisih mutlak per kanal antara keluaran
    # Real-ESRGAN dan LANCZOS 4x adalah 8,6 aras dari 255, dan 19,2% piksel
    # berselisih lebih dari 8 aras. Kalau subprocess-nya diganti LANCZOS,
    # kedua angka itu jadi TEPAT NOL — bukan sekadar mengecil.
    #
    # Ambangnya sengaja dipasang jauh di bawah angka terukur (3,0 dan 5%),
    # bukan mepet: yang dibedakan di sini adalah "beda nyata" lawan "nol
    # mutlak", jadi margin tiga kali lipat masih aman sekaligus tidak rapuh.
    # Angkanya sendiri deterministik (dijaga cek determinisme di atas) dan
    # binernya dipatok sha256, jadi ia tidak bisa bergeser diam-diam.
    _butuh_upscaler()
    asal = _kutout_uji((226, 570))
    esrgan = poster._naikkan_resolusi(asal, 99999)
    lanczos = asal.resize((asal.width * 4, asal.height * 4), Image.Resampling.LANCZOS)
    assert esrgan.size == lanczos.size, \
        f'ukuran tidak sebanding, perbandingan tidak sah: {esrgan.size} vs {lanczos.size}'

    a = list(esrgan.convert('RGB').getdata())
    b = list(lanczos.convert('RGB').getdata())
    selisih = [max(abs(x[0] - y[0]), abs(x[1] - y[1]), abs(x[2] - y[2]))
               for x, y in zip(a, b)]
    rerata = sum(abs(x[k] - y[k]) for x, y in zip(a, b) for k in range(3)) / (3 * len(a))
    porsi = sum(1 for d in selisih if d > 8) / len(selisih)

    assert rerata > 3.0, \
        (f'keluaran upscaler cuma berselisih {rerata:.2f} aras dari LANCZOS 4x — '
         f'nol berarti Real-ESRGAN sudah diganti resize biasa, dan kartu keluar '
         f'seolah HD padahal tidak')
    assert porsi > 0.05, \
        (f'cuma {porsi:.1%} piksel yang berselisih nyata dari LANCZOS 4x — '
         f'bedanya bukan rekonstruksi model, cuma derau pembulatan')


@periksa('rakit() sungguh memanggil _naikkan_resolusi, _perlakukan_latar, dan _perlakukan_karakter')
def _():
    # Temuan review C1. Ketiga fungsi ini adalah SELURUH nilai cabang ini,
    # tapi tak satu pun cek lama membuktikan jalur produksi memanggilnya:
    # cek perlakuan memanggil fungsinya LANGSUNG, dan satu-satunya cek yang
    # menjalankan rakit() sengaja memakai kutout raksasa supaya upscale
    # dilewati lalu tidak menegaskan apa pun soal perlakuan. Menghapus salah
    # satu panggilan dari poster.rakit tetap hijau 81/81 — diverifikasi
    # dengan menghapus ketiganya satu per satu.
    #
    # _naikkan_resolusi diganti perekam yang mengembalikan masukannya apa
    # adanya (bukan meneruskan ke aslinya): yang diuji di sini PEMANGGILANNYA,
    # bukan hasilnya, dan cek ini tidak boleh butuh biner GPU 27MB. Dua yang
    # lain diteruskan ke aslinya supaya poster tetap terakit wajar.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        _buat_akun(akar, 'premium', '9101', n_karakter=3)
        akun, dilewati = antrean.baca(akar)
        assert dilewati == [], dilewati

        jejak = []

        def _rekam_naikkan(im, tinggi_tayang):
            jejak.append('naikkan')
            return im

        naikkan_asli = poster._naikkan_resolusi
        latar_asli = poster._perlakukan_latar
        karakter_asli = poster._perlakukan_karakter
        potong_asli = poster._potong

        def _rekam_latar(im):
            jejak.append('latar')
            return latar_asli(im)

        def _rekam_karakter(im):
            jejak.append('karakter')
            return karakter_asli(im)

        poster._naikkan_resolusi = _rekam_naikkan
        poster._perlakukan_latar = _rekam_latar
        poster._perlakukan_karakter = _rekam_karakter
        poster._potong = lambda berkas, tujuan: Image.new('RGBA', (226, 570), (180, 90, 60, 255))
        try:
            with latar_sementara(Path(t) / 'latar', (800, 900), (20, 20, 20, 255)):
                poster.rakit(akun[0], Path(t) / 'aset')
        finally:
            # Dikembalikan di finally: kalau satu cek gagal di tengah, jembatan
            # yang tertinggal akan membuat cek-cek SESUDAHNYA gagal karena
            # alasan palsu — dan itu jauh lebih mahal daripada satu merah jujur.
            poster._naikkan_resolusi = naikkan_asli
            poster._perlakukan_latar = latar_asli
            poster._perlakukan_karakter = karakter_asli
            poster._potong = potong_asli

    assert jejak.count('naikkan') == 3, \
        (f'_naikkan_resolusi dipanggil {jejak.count("naikkan")}x untuk 3 karakter — '
         f'panggilannya hilang dari poster.rakit, kutout tetap 226x570 dan kartunya buram')
    assert jejak.count('latar') == 1, \
        (f'_perlakukan_latar dipanggil {jejak.count("latar")}x — tanpa blur+redup, '
         f'latar beresolusi penuh membuat karakter selalu terbaca burik di sebelahnya')
    assert jejak.count('karakter') == 3, \
        (f'_perlakukan_karakter dipanggil {jejak.count("karakter")}x untuk 3 karakter — '
         f'structure, sharpen, kontras, dan saturasi tidak pernah kena kutout')


@periksa('tata_letak kebal skala: kotak alfa 4x menghasilkan penempatan yang sama')
def _():
    kotak = [(0, 0, 226, 570)] * 3
    besar = [(0, 0, 904, 2280)] * 3
    assert poster.tata_letak((2353, 2521), kotak) == poster.tata_letak((2353, 2521), besar), \
        ('penempatan bergeser saat kutout di-upscale — upscale seharusnya '
         'mengubah piksel, bukan geometri')


@periksa('akun tanpa poster.png kini berhasil dirakit lewat rakit.jalankan (Perkakas B tersedia)')
def _():
    # Ini titik integrasi yang jadi alasan Task 8 ada: rakit._poster_untuk
    # sudah lama siap memanggil poster.rakit, tinggal menunggu modulnya.
    # _potong dijembatani supaya tes ini tidak bergantung pada Vision
    # sungguhan mendeteksi subjek pada gambar sintetis — itu bukan yang
    # sedang diuji di sini, jalur integrasinya yang diuji.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        _buat_akun(akar, 'premium', '5001', n_karakter=3, poster=False)

        aset = Path(t) / 'aset'
        shutil.copytree(ASET, aset)

        potong_asli = poster._potong
        poster._potong = lambda berkas, tujuan: Image.new('RGBA', (400, 800), (200, 120, 40, 255))
        try:
            with latar_sementara(Path(t) / 'latar', (2353, 2521), (20, 20, 20, 255)):
                dibuat, dilewati, _, _ = rakit.jalankan(akar, tujuan, aset)
        finally:
            poster._potong = potong_asli

        assert dilewati == [], f'akun dengan karakter/ lengkap masih dilewati: {dilewati}'
        assert any('5001-utama' in p.name for p in dibuat), 'kartu utama tidak dibuat'


@periksa('latar tingkat yang hilang menghentikan LEWAT rakit.jalankan (preflight, bukan per-akun)')
def _():
    # Finding 1: prasyarat Perkakas B (biner potong + latar/<tingkat>.png)
    # dulu hanya ketahuan DI DALAM except per-akun, jadi salah pasang lintas
    # antrean dilaporkan sebagai N baris DILEWATI identik dengan exit 0.
    # Cek ini menembak jalur preflight rakit.jalankan, bukan poster.rakit
    # langsung (sudah dijaga cek 'latar tingkat yang hilang menghentikan...'
    # di atas, tapi itu memanggil poster.rakit langsung — tidak membuktikan
    # rakit.jalankan mencegatnya SEBELUM masuk ke loop per-akun).
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        _buat_akun(akar, 'premium', '5001', n_karakter=3, poster=False)

        aset = Path(t) / 'aset'
        shutil.copytree(ASET, aset)

        # Temuan review R1b: preflight cek biner LEBIH DULU daripada latar
        # (rakit.py). Di checkout yang belum mengompilasi potong, GalatFatal
        # yang meletus di sini adalah soal biner, bukan latar — pesannya
        # tidak pernah menyebut 'premium' dan assersi di bawah gagal karena
        # alasan yang tidak relevan dengan yang sedang diuji. poster.POTONG
        # dijembatani ke berkas yang ADA (bukan biner sungguhan) supaya cek
        # ini SELALU menembus ke cek latar, terlepas dari apakah mesin yang
        # menjalankannya sudah mengompilasi potong atau belum — teknik yang
        # sama seperti cek 'biner potong yang belum dikompilasi ...' di
        # bawah, arah sebaliknya.
        import poster as modul_poster
        potong_palsu = Path(t) / 'potong-palsu'
        potong_palsu.write_bytes(b'')
        potong_asli = modul_poster.POTONG
        modul_poster.POTONG = potong_palsu
        try:
            try:
                with latar_sementara(Path(t) / 'latar-kosong', tingkat=()):
                    dibuat, dilewati, _, _ = rakit.jalankan(akar, tujuan, aset)
            except antrean.GalatFatal as e:
                assert 'premium' in str(e), f'pesan tidak menyebut tingkat yang kurang: {e}'
            else:
                raise AssertionError(
                    f'latar hilang malah lolos sebagai skip per-akun: dibuat={dibuat} '
                    f'dilewati={dilewati}')
        finally:
            modul_poster.POTONG = potong_asli


@periksa('biner potong yang belum dikompilasi menghentikan LEWAT rakit.jalankan (preflight)')
def _():
    # Sama seperti cek di atas tapi untuk prasyarat B yang kedua. Biner
    # dijembatani via poster.POTONG (bukan dihapus dari disk sungguhan —
    # mesin CI ini punya binernya, dan tes tidak boleh bergantung pada
    # keberadaan berkas lokal yang bukan bagian repo).
    import poster as modul_poster
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        _buat_akun(akar, 'premium', '5001', n_karakter=3, poster=False)

        potong_asli = modul_poster.POTONG
        modul_poster.POTONG = Path(t) / 'potong-tidak-ada'
        try:
            try:
                dibuat, dilewati, _, _ = rakit.jalankan(akar, tujuan, ASET)
            except antrean.GalatFatal as e:
                assert 'dikompilasi' in str(e).lower(), f'pesan tidak sebut kompilasi: {e}'
                assert 'swiftc' in str(e), f'pesan tidak beri jalan keluar: {e}'
            else:
                raise AssertionError(
                    f'biner belum dikompilasi malah lolos sebagai skip per-akun: '
                    f'dibuat={dibuat} dilewati={dilewati}')
        finally:
            modul_poster.POTONG = potong_asli


@periksa('GalatFatal dari dalam badan akun tetap menembus, tidak tertelan jadi skip')
def _():
    # Finding 1, separuh kedua: preflight saja tidak cukup kalau except
    # Exception di dalam loop menelan GalatFatal yang meletus BELAKANGAN
    # (mis. dari cabang lain yang tidak lewat preflight ini). _poster_untuk
    # dijembatani supaya GalatFatal-nya sintetis dan tidak bergantung pada
    # cara nyata memicunya.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        _buat_akun(akar, 'premium', '5001', poster=True)

        asli = rakit._poster_untuk
        def _meledak(akun, aset, catat=None):
            raise antrean.GalatFatal('salah pasang sintetis untuk tes')
        rakit._poster_untuk = _meledak
        try:
            try:
                rakit.jalankan(akar, tujuan, ASET)
            except antrean.GalatFatal:
                pass
            else:
                raise AssertionError('GalatFatal dari badan akun malah tertelan jadi skip')
        finally:
            rakit._poster_untuk = asli


@periksa('rerun yang menghasilkan lebih sedikit kartu slide tidak menyisakan berkas lama')
def _():
    # Finding 2: nama berkas keluaran ditulis dengan overwrite polos. Kalau
    # lari kedua menghasilkan LEBIH SEDIKIT kartu slide daripada lari
    # pertama, berkas lebih dari lari pertama bertahan di disk walau
    # ringkasan lari kedua tidak pernah menyebutnya.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        folder = _buat_akun(akar, 'premium', '5001', n_slide=4, poster=True)
        dibuat1, dilewati1, _, _ = rakit.jalankan(akar, tujuan, ASET)
        assert dilewati1 == [], dilewati1
        assert sorted(p.name for p in dibuat1) == \
            ['5001-slide-1.webp', '5001-slide-2.webp', '5001-utama.webp']

        # Pemilik menghapus dua screenshot slide lalu menjalankan ulang.
        #
        # `ulang=True` karena sejak 14 Agu akun yang kartunya sudah ada
        # dilewati: tanpa itu lari kedua tidak merakit apa pun dan cek ini
        # hijau tanpa pernah menguji pembuangan sisanya. Jaminannya tidak
        # berubah, cuma perlu dipicu.
        (folder / 'slide' / '3.png').unlink()
        (folder / 'slide' / '4.png').unlink()
        dibuat2, dilewati2, _, _ = rakit.jalankan(akar, tujuan, ASET, ulang=True)
        assert dilewati2 == [], dilewati2
        nama2 = sorted(p.name for p in dibuat2)
        assert nama2 == ['5001-slide-1.webp', '5001-utama.webp'], nama2

        di_disk = sorted(p.name for p in (tujuan / '5001').glob('*.webp'))
        assert di_disk == nama2, \
            f'folder masih menyimpan sisa lari pertama: disk={di_disk} ringkasan={nama2}'


@periksa('pose menjulur lebar melahirkan peringatan bahwa karakter diperkecil')
def _():
    # Menggantikan cek 'kutout terlalu lebar ... terpotong'. Peringatan itu
    # kini mustahil menyala: tata_letak menyusutkan ketiganya sampai muat
    # berikut celah, jadi tidak ada yang bisa terpotong tepi panggung. Cek yang
    # menjaga hal yang tidak bisa terjadi adalah cek yang berbohong soal
    # liputannya.
    #
    # Yang masih perlu diketahui pemilik adalah HARGA dari penyusutan itu:
    # kartu yang tampak lebih kecil dari biasanya bukan kebetulan.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        tujuan = Path(t) / 'siap-upload'
        folder = _buat_akun(akar, 'premium', '5001', n_karakter=3, poster=False)
        for i, warna in enumerate(((255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)), 1):
            Image.new('RGBA', (60, 60), warna).save(folder / 'karakter' / f'{i}.png')

        aset = Path(t) / 'aset'
        shutil.copytree(ASET, aset)

        potong_asli = poster._potong
        def _potong_lebar(berkas, tujuan_):
            # Karakter 2 sengaja menjulur mendatar, meniru senjata naga 777.
            if berkas.stem == '2':
                return Image.new('RGBA', (1400, 1000), (200, 30, 30, 255))
            return Image.new('RGBA', (400, 800), (30, 200, 30, 255))
        poster._potong = _potong_lebar
        try:
            dibuat, dilewati, peringatan, _ = rakit.jalankan(akar, tujuan, aset)
        finally:
            poster._potong = potong_asli

        assert dilewati == [], dilewati
        assert any('5001-utama' in p.name for p in dibuat), 'kartu malah tidak dibuat'
        assert len(peringatan) == 1, f'penyusutan lewat tanpa peringatan: {peringatan}'
        kode, pesan = peringatan[0]
        assert kode == '5001', peringatan
        assert 'diperkecil' in pesan, f'peringatan tidak menyebut penyusutannya: {pesan}'


@periksa('folder titik (.Trashes) di antrean diabaikan, bukan dilaporkan sebagai akun rusak')
def _():
    # Finding "Also fix": skenario exFAT/HP yang sama dengan companion
    # AppleDouble juga menaruh FOLDER titik, bukan cuma berkas titik.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t)
        _buat_akun(akar, 'premium', '5001')
        (akar / '.Spotlight-V100').mkdir()
        (akar / 'premium' / '.Trashes').mkdir()
        akun, dilewati = antrean.baca(akar)
        assert dilewati == [], f'folder titik malah dilaporkan sebagai akun rusak: {dilewati}'
        assert len(akun) == 1 and akun[0].kode == '5001'


@periksa('tiga berkas karakter yang isinya identik memicu PERINGATAN, kartunya tetap dibuat')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        # _buat_akun sudah menulis tiga berkas identik; itulah keadaan yang diuji.
        _buat_akun(akar, 'premium', '5001')
        akun, dilewati = antrean.baca(akar)
        assert len(akun) == 1, f'akun malah dilewati: {dilewati}'
        assert any('identik' in p for p in akun[0].peringatan), \
            f'tidak ada peringatan karakter kembar: {akun[0].peringatan}'


@periksa('tiga berkas karakter yang benar-benar berbeda tidak dituduh kembar')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        folder = _buat_akun(akar, 'premium', '5002')
        # Timpa dengan warna berbeda-beda. Tanpa ini ceknya merah karena
        # fixture-nya memang kembar, bukan karena kodenya salah.
        for i, warna in enumerate(((255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)), 1):
            Image.new('RGBA', (60, 60), warna).save(folder / 'karakter' / f'{i}.png')

        akun, _ = antrean.baca(akar)
        assert not any('identik' in p for p in akun[0].peringatan), \
            f'karakter berbeda malah dituduh kembar: {akun[0].peringatan}'


@periksa('akun berposter.png sendiri tidak dituduh kembar walau karakter/ kebetulan identik')
def _():
    # Fix round 1: untuk akun begini, rakit._poster_untuk mengembalikan
    # Image.open(akun.poster) langsung — poster.rakit() tidak pernah
    # dipanggil, dan karakter/ tidak pernah dibaca sama sekali. Peringatan
    # kembar di sini adalah peringatan PALSU: ia menuduh karakter/ akan
    # dipajang berulang, padahal karakter/ tidak dipakai sama sekali.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        # _buat_akun menulis tiga berkas karakter identik dan poster.png —
        # persis kombinasi yang harus TIDAK memicu peringatan.
        _buat_akun(akar, 'premium', '5003', poster=True)
        akun, dilewati = antrean.baca(akar)
        assert dilewati == [], dilewati
        assert akun[0].peringatan == [], \
            f'akun berposter.png sendiri dituduh kembar padahal karakter/ tidak dipakai: {akun[0].peringatan}'


def _jalankan(periksaan):
    """Jalankan satu daftar (nama, fungsi), cetak status tiap baris, balikkan jumlah gagal.

    Dipisah dari blok __main__ supaya bisa dites langsung dengan daftar cek
    buatan (lihat cek 'cek yang meledak ...' di bawah) tanpa menyentuh
    PERIKSAAN global atau menjalankan lewat subprocess.

    Menangkap Exception, bukan cuma AssertionError: alat ini adalah
    satu-satunya penjamin bahwa Perkakas A dan B masih bekerja, jadi satu cek
    yang meledak dengan exception LAIN (mis. GalatFatal yang lolos tak
    tertangkap dari sebuah cek, atau bug di kode cek itu sendiri) tidak boleh
    menjatuhkan seluruh proses lewat traceback mentah — itu berarti tidak ada
    baris GAGAL, tidak ada total, dan cek-cek sesudahnya tidak pernah
    dijalankan. Jenis exception-nya disertakan di pesan supaya crash (bug di
    kode) tidak disalahartikan sebagai assersi yang sengaja gagal.
    """
    gagal = 0
    dilewati = 0
    for nama, fungsi in periksaan:
        try:
            fungsi()
            print(f'  ok   {nama}')
        except Lewat as e:
            dilewati += 1
            print(f'  lewat {nama}: {e}')
        except AssertionError as e:
            gagal += 1
            print(f'  GAGAL {nama}: {e}')
        except Exception as e:
            gagal += 1
            print(f'  GAGAL {nama}: [{type(e).__name__}] {e}')
    lulus = len(periksaan) - gagal - dilewati
    ekor = f' ({dilewati} dilewati)' if dilewati else ''
    print(f'\n{lulus}/{len(periksaan) - dilewati} lulus{ekor}')
    return gagal


@periksa('cek yang meledak dengan exception non-AssertionError dilaporkan gagal, cek lain tetap jalan, total tetap tercetak')
def _():
    # Finding R1a: runner lama cuma menangkap AssertionError. Sebuah exception
    # LAIN (mis. GalatFatal yang lolos tak tertangkap dari dalam satu cek,
    # atau bug biasa di kode ceknya sendiri) dulu menjatuhkan SELURUH proses
    # lewat traceback mentah — tidak ada baris GAGAL, tidak ada total, cek-cek
    # berikutnya tidak pernah dijalankan. Terukur langsung 8 Agu: dengan biner
    # potong dipindah, larinya mati di tengah jalan — baris terakhir yang
    # tercetak "ok", lalu traceback, lalu tidak ada apa-apa.
    #
    # Daftar cek SINTETIS dipakai di sini, bukan PERIKSAAN sungguhan —
    # tesnya tidak boleh bergantung pada isi berkas ini yang bisa berubah.
    dipanggil = []

    def _ok():
        dipanggil.append('ok')

    def _meledak():
        dipanggil.append('meledak')
        raise ValueError('bukan assersi — mensimulasikan bug di kode cek')

    def _lulus():
        dipanggil.append('lulus')

    daftar = [('cek pertama', _ok), ('cek meledak', _meledak), ('cek terakhir', _lulus)]

    keluar = io.StringIO()
    with contextlib.redirect_stdout(keluar):
        gagal = _jalankan(daftar)

    assert dipanggil == ['ok', 'meledak', 'lulus'], \
        f'cek sesudah yang meledak tidak ikut jalan — proses berhenti di tengah: {dipanggil}'
    assert gagal == 1, f'jumlah gagal salah: {gagal}'
    keluaran = keluar.getvalue()
    assert 'GAGAL cek meledak' in keluaran, \
        f'cek yang meledak tidak dilaporkan sebagai gagal: {keluaran!r}'
    assert 'ValueError' in keluaran, \
        f'jenis exception tidak disertakan — crash tak bisa dibedakan dari assersi gagal: {keluaran!r}'
    assert '2/3 lulus' in keluaran, f'total tidak tercetak dengan benar: {keluaran!r}'


@periksa('cek yang melempar Lewat dilaporkan lewat, bukan gagal, dan tidak menjatuhkan total')
def _():
    def _dilewati():
        raise Lewat('biner upscaler belum diunduh')

    def _lulus():
        assert True

    daftar = [('yang dilewati', _dilewati), ('yang lulus', _lulus)]
    tangkap = io.StringIO()
    with contextlib.redirect_stdout(tangkap):
        gagal = _jalankan(daftar)
    keluaran = tangkap.getvalue()

    assert gagal == 0, f'cek yang dilewati malah dihitung gagal ({gagal})'
    # Temuan review (minor): 'lewat' saja juga cocok dengan potongan kata di
    # dalam ekor ringkasan ('1 dilewati'), jadi assersi lama tetap hijau walau
    # baris per-cek-nya hilang sama sekali dan pemilik tidak pernah tahu cek
    # MANA yang tidak dijalankan. Yang dituntut sekarang baris per-cek itu
    # sendiri, lengkap dengan namanya.
    assert 'lewat yang dilewati' in keluaran, \
        (f'tidak ada BARIS per-cek yang menandai cek mana yang dilewati '
         f'(ekor ringkasan tidak cukup):\n{keluaran}')
    assert 'biner upscaler belum diunduh' in keluaran, \
        'alasan melewati tidak ikut tercetak, jadi pemilik tidak tahu apa yang kurang'
    assert '2/2 lulus' not in keluaran, \
        'yang dilewati ikut dihitung lulus — itu menyesatkan, ia tidak diuji'


import potong_item


class latar_sementara:
    """Tunjuk poster.LATAR_BAWAAN ke folder sementara selama satu cek.

    Latar hidup di latar/, di luar mesin/, karena ia aset yang
    diganti-ganti pemilik. Cek tidak boleh menyentuh folder itu, jadi
    konstantanya ditimpa sementara dan dikembalikan di `finally`.
    """

    def __init__(self, folder, ukuran=(2353, 2521), warna=(10, 10, 10, 255),
                 tingkat=('premium',)):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        for t in tingkat:
            Image.new('RGBA', ukuran, warna).save(self.folder / f'{t}.png')

    def __enter__(self):
        self.asli = poster.LATAR_BAWAAN
        poster.LATAR_BAWAAN = self.folder
        return self.folder

    def __exit__(self, *a):
        poster.LATAR_BAWAAN = self.asli
        return False


def _layar_fashion_palsu(lebar=1600, tinggi=739, kanan=330, alas=135, n=8,
                         ikon_terang=False, kisi_kanan=False):
    """Layar Fashion tiruan: blok terang di posisi angka, jarak sesuai pecahan asli.

    Dibangun di dalam tes, bukan dimuat dari screenshot: berkas asli memuat data
    akun dan tidak boleh masuk repo, dan cek yang bergantung berkas di luar repo
    akan hijau tanpa memeriksa apa pun di mesin lain.

    `ikon_terang` menambahkan gumpalan terang TEPAT DI ATAS tiap angka, meniru
    ikon rambut putih, rompi, dan celana di strip sungguhan. Tanpa itu fixture
    ini terlalu bersih: latar gelap polos membuat pencarian fase selalu benar,
    sehingga cacat yang muncul di layar nyata — dasar ikon ikut tercetak skor
    dan menarik fase naik — tidak pernah bisa dilahirkan di sini.
    """
    from PIL import ImageDraw
    jarak = potong_item.JARAK * tinggi
    im = Image.new('RGB', (lebar, tinggi), (14, 10, 20))
    d = ImageDraw.Draw(im)
    for i in range(n):
        y = alas + jarak * i
        if y > tinggi:
            break
        if ikon_terang:
            d.ellipse([kanan - jarak * 0.80, y - jarak * 0.85,
                       kanan - jarak * 0.10, y - jarak * 0.22], fill=(238, 238, 245))
        d.rectangle([kanan - jarak * 0.42, y - jarak * 0.16, kanan, y], fill=(255, 255, 255))
        # Ekor anti-alias di bawah angka: baris redup yang jatuh DI BAWAH ambang
        # keras pencarian fase, tapi masih terlihat mata sebagai dasar angka.
        # Tanpa ini fixture berdigit bertepi tajam, dan cacat yang memotong
        # angka di FF-REGULER-6002 tidak bisa lahir di uji.
        # 200, bukan 150: fixture memakai putih murni sehingga ambang keras
        # terhitung 255 dan ambang lunak jatuh di 158. Ekor bernilai 150 akan
        # berada DI BAWAH keduanya — itu meniru ekor yang tak terlihat siapa
        # pun, bukan ekor yang terlihat mata tapi terlewat ambang keras.
        # 200 duduk di antara keduanya, persis keadaan yang diuji.
        d.rectangle([kanan - jarak * 0.42, y, kanan, y + jarak * 0.05],
                    fill=(200, 200, 200))
        if kisi_kanan:
            # Kisi item yang duduk rapat di kanan strip, seperti pada layar
            # berbahasa Indonesia. Terang dan lebar — inilah yang menarik
            # pencarian kolom ke kanan kalau tidak dikunci.
            d.rectangle([kanan + jarak * 0.18, y - jarak * 0.80,
                         kanan + jarak * 1.40, y - jarak * 0.05],
                        fill=(215, 215, 225))
        # Penanda kecil yang BERBEDA tiap petak. Tanpa ini semua petak identik,
        # dan cek 'baris "item:" menentukan petak' lulus karena kebetulan:
        # memotong petak 1 atau petak 4 menghasilkan piksel yang sama persis,
        # jadi ia tidak pernah membuktikan pilihannya benar-benar berlaku.
        d.rectangle([kanan - jarak * 0.70, y - jarak * 0.55,
                     kanan - jarak * 0.70 + jarak * 0.05 * (i % 5 + 1),
                     y - jarak * 0.45], fill=(120, 200, 255))
    return im, jarak


@periksa('kalibrasi menemukan sendiri kolom dan fase strip, tanpa koordinat dipaku')
def _():
    # Koordinat pernah dipaku dari satu screenshot dan langsung meleset pada
    # screenshot berikutnya: bahasa UI menggeser strip, daftar bisa tergulir,
    # dan kompresi WhatsApp menskala x dan y sedikit berbeda.
    for lebar, tinggi, kanan, alas in ((1600, 739, 330, 135),
                                       (2868, 1320, 609, 240),
                                       (1280, 590, 262, 108)):
        im, jarak = _layar_fashion_palsu(lebar, tinggi, kanan, alas)
        k_kanan, k_alas, k_jarak = potong_item.kalibrasi(im)
        assert abs(k_kanan - kanan) <= max(3, lebar * 0.004), \
            f'{lebar}x{tinggi}: kolom ketemu {k_kanan}, seharusnya ~{kanan}'
        # fase boleh berbeda satu kelipatan jarak — yang penting sisanya cocok
        sisa = abs(k_alas - alas) % jarak
        assert min(sisa, jarak - sisa) <= jarak * 0.10, \
            f'{lebar}x{tinggi}: fase ketemu {k_alas:.0f}, seharusnya ~{alas} (mod {jarak:.0f})'


@periksa('_perhalus_alas menarik fase yang meleset kembali ke dasar angka')
def _():
    # Cacat nyata 9 Agu pada IMG_5924.PNG: keempat angka terpotong 6-7px.
    # Sebabnya BUKAN kotak yang kekecilan melainkan dasar angka yang dideteksi
    # meleset ~19px ke ATAS — pencarian fase memakai pita selebar 0,62 jarak,
    # dan dasar ikon yang terang (rambut putih, rompi, celana) ikut tercetak
    # skor sehingga fase yang sedikit naik menang.
    #
    # Yang diuji di sini KONTRAK penguncinya, bukan lewat layar tiruan. Sempat
    # dicoba dengan menambahkan ikon terang ke fixture, tapi tiruan itu tidak
    # berhasil melahirkan biasnya — dan cek yang tidak pernah bisa merah adalah
    # cek yang berbohong soal liputannya. Menyuapkan fase yang sengaja meleset
    # menguji persis kemampuan yang dibutuhkan.
    from PIL import ImageDraw
    lebar, tinggi, kanan, alas = 2868, 1320, 609, 240
    im, jarak = _layar_fashion_palsu(lebar, tinggi, kanan, alas, ikon_terang=True)

    # Ambang lunak, seperti yang dipakai kalibrasi untuk penguncian — supaya
    # ekor di bawah digit ikut terbaca.
    lembut = im.convert('L').point(lambda v: 255 if v >= 110 else 0)
    # Yang dituju dasar YANG TERLIHAT, termasuk ekornya — bukan dasar digit
    # keras. Itu memang yang harus dikejar: ekor yang terpotong tetap terbaca
    # sebagai angka terpenggal di kartu jadi.
    sasaran = alas + jarak * 0.05
    for meleset in (-19, -9, +7, +15):
        hasil = potong_item._perhalus_alas(lembut, 0, kanan, alas + meleset, jarak)
        sisa = abs(hasil - sasaran) % jarak
        sisa = min(sisa, jarak - sisa)
        assert sisa <= 3, (
            f'fase meleset {meleset:+d}px tidak tertarik kembali: hasil {hasil:.0f}, '
            f'seharusnya ~{sasaran:.0f} (masih meleset {sisa:.0f}px)')


@periksa('bingkai seleksi dibuang apa pun warnanya, tapi barang berwarna selamat')
def _():
    # Layar Fashion SELALU menandai satu slot yang sedang dilihat, jadi di
    # screenshot mana pun ada satu petak yang terlihat beda sendiri. Pemilik
    # menunjuknya pada FF-PELAJAR-6001 (bingkai kuning), lalu FF-REGULER-6002
    # ternyata memakai bingkai BIRU — tema UI-nya berbeda.
    #
    # Maka pendeteksinya dibuat BUTA WARNA. Terukur pada petak biru: kolom
    # bingkai berkecerahan 106-132 dengan kejenuhan 100-105, sedangkan latar
    # petak 49 dengan kejenuhan 28-60. Yang membedakan bukan warnanya melainkan
    # "jauh lebih terang daripada latar petak sendiri, dan jenuh".
    #
    # Bahayanya: skin senjata berwarna adalah barang yang dibayar pembeli.
    # Pengamannya BENTUK — bingkai menempel tepi dan melapisi sisinya hampir
    # penuh; barang duduk di tengah.
    from PIL import ImageDraw

    def _petak(warna_bingkai=None, warna_barang=None):
        im = Image.new('RGB', (81, 82), (26, 20, 34))
        d = ImageDraw.Draw(im)
        if warna_barang:
            d.ellipse([26, 26, 54, 54], fill=warna_barang)
        if warna_bingkai:
            d.rectangle([4, 4, 76, 77], outline=warna_bingkai, width=3)
        return im

    def _tengah(im):
        return im.crop((24, 24, 57, 57)).tobytes()

    for nama, warna in (('kuning', (238, 194, 46)), ('biru', (64, 150, 240)),
                        ('ungu', (168, 84, 232))):
        berbingkai = _petak(warna_bingkai=warna)
        bersih = potong_item.bersihkan_bingkai(berbingkai)
        px = bersih.load()
        tepi = sum(1 for y in range(bersih.height) for x in range(bersih.width)
                   if (x < 8 or x >= bersih.width - 8 or y < 8 or y >= bersih.height - 8)
                   and max(px[x, y]) - min(px[x, y]) > 60
                   and sum(px[x, y]) / 3 > 70)
        assert tepi < 40, f'bingkai {nama} masih tersisa {tepi} piksel di tepi'

    for nama, warna in (('emas', (226, 176, 42)), ('biru', (70, 150, 235))):
        barang = _petak(warna_barang=warna)
        sesudah = potong_item.bersihkan_bingkai(barang)
        assert _tengah(sesudah) == _tengah(barang), \
            f'barang {nama} di tengah petak ikut diubah — itu merusak dagangan'

    polos = _petak()
    assert potong_item.bersihkan_bingkai(polos).tobytes() == polos.tobytes(), \
        'petak tanpa bingkai ikut diubah'


@periksa('_perhalus_kanan menarik kolom yang meleset kembali ke tepi angka')
def _():
    # Cacat kembar dari _perhalus_alas, di sumbu lain. Layar Fashion berbahasa
    # Indonesia menaruh kisi item rapat di kanan strip; kisi itu terang, jadi
    # pencarian kolom tertarik ke sana. Diukur 9 Agu pada FF-REGULER-6001:
    # kolom meleset 18-19px, yaitu 23% lebar petak, dan tiap potongan memuat
    # sepotong kisi di tepinya.
    lebar, tinggi, kanan, alas = 1600, 739, 330, 135
    im, jarak = _layar_fashion_palsu(lebar, tinggi, kanan, alas,
                                     ikon_terang=True, kisi_kanan=True)
    lembut = im.convert('L').point(lambda v: 255 if v >= 110 else 0)
    for meleset in (-12, -5, +9, +18):
        hasil = potong_item._perhalus_kanan(lembut, 0, kanan + meleset, alas, jarak)
        assert abs(hasil - kanan) <= 3, (
            f'kolom meleset {meleset:+d}px tidak tertarik kembali: hasil {hasil}, '
            f'seharusnya ~{kanan}')


@periksa('penguncian memakai ambang lunak, jadi ekor anti-alias angka ikut terbaca')
def _():
    # FF-REGULER-6002 tetap memotong angka 3-4px walau kalibrasinya sudah
    # "benar": penguncian memakai gambar berambang KERAS, yang memotong ekor
    # anti-alias di bawah digit — padahal ekor itulah yang mata lihat sebagai
    # dasar angka. Ambang keras tetap dipakai pencarian fase supaya derau tidak
    # ikut; penguncian memakai ambang lunak tersendiri.
    lebar, tinggi, kanan, alas = 1600, 739, 330, 135
    im, jarak = _layar_fashion_palsu(lebar, tinggi, kanan, alas, ikon_terang=True)
    kal = potong_item.kalibrasi(im)
    ekor = alas + jarak * 0.05          # dasar yang terlihat, termasuk ekornya
    sisa = abs(kal[1] - ekor) % jarak
    sisa = min(sisa, jarak - sisa)
    assert sisa <= 3, (
        f'dasar terkunci di {kal[1]:.0f}, sedangkan dasar yang terlihat ~{ekor:.0f} — '
        f'ekor anti-alias tidak ikut terbaca, angka akan terpotong')


@periksa('angka ikut utuh di dalam petak yang dipotong, tidak terpenggal di bawah')
def _():
    # Terpisah dari cek di atas: yang ini menuntut hasil AKHIR, bukan kalibrasi.
    # Dasar angka boleh tepat tapi napas di bawahnya kurang, dan pemilik tetap
    # menerima angka terpenggal.
    lebar, tinggi, kanan, alas = 2868, 1320, 609, 240
    im, jarak = _layar_fashion_palsu(lebar, tinggi, kanan, alas, ikon_terang=True)
    kal = potong_item.kalibrasi(im)
    n = potong_item.nomor_pertama_utuh(kal, im.size)
    _, _, _, bawah = potong_item.kotak_petak(kal, n)
    dasar_nyata = alas + jarak * round((bawah - alas) / jarak)
    assert bawah >= dasar_nyata, (
        f'tepi bawah petak {bawah} berada DI ATAS dasar angka {dasar_nyata:.0f} — '
        f'angkanya terpotong')


@periksa('gambar tanpa strip ikon DITOLAK, bukan dipotong di tempat asal')
def _():
    # Empat layar Armory pemilik sempat lolos di ambang 4 dengan mencocokkan
    # daftar senjatanya — potongan sampah yang tidak kelihatan salah.
    polos = Image.new('RGB', (1600, 739), (30, 24, 40))
    try:
        potong_item.kalibrasi(polos)
    except potong_item.GagalKalibrasi as e:
        assert 'Fashion' in str(e), f'pesan tidak menyebut layar yang dibutuhkan: {e}'
    else:
        raise AssertionError('gambar tanpa strip malah dikalibrasi')


@periksa('petak membingkai angka rata kanan-bawah, dan rasionya ~ slot template')
def _():
    # Dua keluhan pemilik yang tidak terjaga cek mana pun sebelumnya: angka tidak
    # rata kanan, lalu angka menyentuh lengkung sudut slot. Rentangnya LITERAL,
    # sengaja tidak diturunkan dari konstanta yang dijaga — cek yang menghitung
    # harapannya dari konstanta itu ikut bergeser saat konstantanya digeser, dan
    # lolos mutasi tanpa menjaga apa pun. Sudah kejadian sekali di sini.
    with tempfile.TemporaryDirectory() as t:
        im, jarak = _layar_fashion_palsu()
        layar = Path(t) / 'fashion.png'
        im.save(layar)
        keluar = potong_item.potong(layar, Path(t) / 'keluar', [1])[0]
        petak = Image.open(keluar).convert('L')

        bb = petak.point(lambda v: 255 if v > 200 else 0).getbbox()
        assert bb is not None, 'blok angka tidak masuk ke dalam petak sama sekali'

        inset_kanan = petak.width - bb[2]
        inset_bawah = petak.height - bb[3]
        assert 3 <= inset_kanan <= 14, \
            f'angka berjarak {inset_kanan}px dari tepi kanan — rata kanan berarti 3..14px'
        assert 4 <= inset_bawah <= 18, \
            f'angka berjarak {inset_bawah}px dari tepi bawah — terlalu rapat akan ' \
            f'terbaca terpotong oleh lengkung sudut slot'

        rasio_slot = template.SLOT_ITEM[0][2] / template.SLOT_ITEM[0][3]
        rasio_petak = petak.width / petak.height
        assert abs(rasio_petak - rasio_slot) < 0.03, \
            f'rasio petak {rasio_petak:.3f} jauh dari slot {rasio_slot:.3f} — ' \
            f'isinya akan terpotong saat dipaskan'


@periksa('petak yang tepinya keluar gambar tidak ikut dipotong buntung')
def _():
    # Fase pola sering mulai di atas tepi atas, jadi petak nomor 1 belum tentu
    # utuh. Memotongnya begitu saja menghasilkan ikon terpenggal yang lolos ke
    # kartu tanpa kelihatan salah.
    with tempfile.TemporaryDirectory() as t:
        im, jarak = _layar_fashion_palsu(alas=int(potong_item.JARAK * 739 * 0.5))
        layar = Path(t) / 'fashion.png'
        im.save(layar)
        kal = potong_item.kalibrasi(im)
        awal = potong_item.nomor_pertama_utuh(kal, im.size)
        assert awal >= 2, f'petak pertama dianggap utuh padahal terpotong tepi atas (awal={awal})'

        muat = potong_item.jumlah_muat(kal, im.size)
        for nomor in range(1, muat + 1):
            _, atas, _, bawah = potong_item.kotak_petak(kal, awal + nomor - 1)
            assert atas >= 0 and bawah <= im.height, \
                f'petak {nomor} keluar gambar: y {atas}..{bawah} pada tinggi {im.height}'

        try:
            potong_item.potong(layar, Path(t) / 'keluar', [muat + 1])
        except ValueError as e:
            assert 'cuma 1..' in str(e), f'pesan tidak menyebut batasnya: {e}'
        else:
            raise AssertionError('petak di luar jangkauan malah dipotong')


@periksa('petak cukup tinggi untuk ikon terjangkung, tidak memenggal pinggangnya')
def _():
    # Keluhan pemilik: ikon celana terpotong pinggangnya. Ikon di strip tidak
    # sama tinggi — kepala dan masker pendek, celana dan baju menjulang. Kotak
    # yang pas untuk yang pendek memenggal yang jangkung.
    #
    # Diukur pada screenshot pemilik: ikon terjangkung mencapai ~0,86 jarak di
    # atas alas angka. Cek ini menggambar ikon setinggi itu lalu memastikan ia
    # masuk UTUH beserta sedikit ruang — bukan sekadar "ada isinya".
    from PIL import ImageDraw
    TINGGI_IKON = 0.83      # pecahan jarak, LITERAL — bukan diturunkan dari
                            # TINGGI_PETAK, supaya mengecilkan kotak jadi merah
    with tempfile.TemporaryDirectory() as t:
        lebar, tinggi = 1600, 739
        jarak = potong_item.JARAK * tinggi
        kanan, alas = 330, 135
        im = Image.new('RGB', (lebar, tinggi), (14, 10, 20))
        d = ImageDraw.Draw(im)
        for i in range(8):
            y = alas + jarak * i
            if y > tinggi:
                break
            d.rectangle([kanan - jarak * 0.42, y - jarak * 0.16, kanan, y], fill=(255, 255, 255))
            # "ikon" jangkung: balok abu tepat di atas angka
            d.rectangle([kanan - jarak * 0.62, y - jarak * TINGGI_IKON,
                         kanan - jarak * 0.30, y - jarak * 0.22], fill=(150, 150, 160))
        layar = Path(t) / 'fashion.png'
        im.save(layar)

        keluar = potong_item.potong(layar, Path(t) / 'keluar', [1])[0]
        petak = Image.open(keluar).convert('L')
        # baris teratas yang punya isi (ikon abu atau angka putih)
        bb = petak.point(lambda v: 255 if v > 90 else 0).getbbox()
        assert bb is not None, 'petak kosong — tidak ada ikon maupun angka'
        assert bb[1] >= 2, \
            f'isi petak menyentuh tepi atas (baris {bb[1]}) — ikon jangkung ' \
            f'seperti celana akan terpenggal pinggangnya'


def _akun_dengan_layar(akar, kode='7001', pilihan=None):
    """Folder akun lengkap yang ikonnya belum dipotong, plus layar Fashion palsu."""
    folder = _buat_akun(akar, 'premium', kode, n_item=0, poster=True)
    im, _ = _layar_fashion_palsu()
    im.save(folder / 'fashion.png')
    baris = 'harga: 750.000\n' + (f'item: {" ".join(map(str, pilihan))}\n' if pilihan else '')
    (folder / 'info.txt').write_text(baris)
    return folder


@periksa('satu klik cukup: item/ kosong + layar Fashion -> ikon dipotong sendiri')
def _():
    # Sebelumnya pemilik harus menjalankan dua program: potong ikon dulu, baru
    # rakit. item/ kini HASIL, bukan masukan, selama layar Fashion-nya ada.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        folder = _akun_dengan_layar(akar)
        assert not list((folder / 'item').glob('*.png')), 'prasyarat: item/ harus kosong'

        with latar_sementara(Path(t) / 'latar'):
            dibuat, dilewati, _, _ = rakit.jalankan(akar, Path(t) / 'keluar', ASET)

        assert dilewati == [], f'akun berlayar Fashion malah dilewati: {dilewati}'
        assert any('7001-utama' in p.name for p in dibuat), 'kartu utama tidak dibuat'
        hasil = sorted((folder / 'item').glob('*.png'))
        assert len(hasil) == 4, f'item/ berisi {len(hasil)} berkas, harus tepat 4'


@periksa('baris "item:" menentukan petak, dan berlaku tanpa mengosongkan item/ dulu')
def _():
    # item/ diisi ulang tiap lari. Kalau tidak, mengubah pilihan di info.txt
    # tidak akan pernah terlihat sampai foldernya dihapus manual — persis jenis
    # kejutan yang bikin orang mengira perkakasnya rusak.
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        folder = _akun_dengan_layar(akar, pilihan=[1, 2, 3, 4])
        # Sisa lari lama: tujuh berkas, lebih banyak daripada yang akan dipakai.
        # Tanpa pembersihan, tiga di antaranya bertahan dan lari berikutnya
        # melihat tujuh gambar di item/ — folder langsung dilewati.
        for i in range(1, 8):
            Image.new('RGB', (40, 40), (i * 20, 0, 0)).save(folder / 'item' / f'{i}.png')
        with latar_sementara(Path(t) / 'latar'):
            rakit.jalankan(akar, Path(t) / 'keluar', ASET)
        tersisa = sorted((folder / 'item').glob('*.png'))
        assert len(tersisa) == 4, \
            f'item/ menyisakan {len(tersisa)} berkas dari lari sebelumnya, harus 4'
        awal = (folder / 'item' / '1.png').read_bytes()

        # ganti pilihan TANPA menyentuh item/
        #
        # `ulang=True` karena sejak 14 Agu akun yang kartunya sudah ada
        # dilewati, dan penandanya cuma melihat folder keluaran — ia tidak tahu
        # info.txt berubah. Yang diuji di sini tetap sama: begitu akunnya
        # DIRAKIT, item/ diisi ulang tanpa perlu dikosongkan dulu.
        (folder / 'info.txt').write_text('harga: 750.000\nitem: 4 5 6 7\n')
        with latar_sementara(Path(t) / 'latar2'):
            rakit.jalankan(akar, Path(t) / 'keluar', ASET, ulang=True)
        sesudah = (folder / 'item' / '1.png').read_bytes()

        assert awal != sesudah, \
            'mengubah baris "item:" tidak mengubah apa pun — item/ tidak diisi ulang'


@periksa('dua gambar di akar folder akun dilewati, bukan ditebak mana yang benar')
def _():
    with tempfile.TemporaryDirectory() as t:
        akar = Path(t) / 'antrean'
        folder = _akun_dengan_layar(akar)
        im, _ = _layar_fashion_palsu()
        im.save(folder / 'fashion-lain.png')
        akun, dilewati = antrean.baca(akar)
        assert akun == [], 'dua gambar di akar malah diterima'
        assert len(dilewati) == 1 and '2 gambar' in dilewati[0][1], \
            f'alasan tidak menjelaskan: {dilewati}'


if __name__ == '__main__':
    sys.exit(1 if _jalankan(PERIKSAAN) else 0)
