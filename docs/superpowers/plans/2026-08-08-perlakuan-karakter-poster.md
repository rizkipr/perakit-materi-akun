# Perlakuan Karakter pada Poster — Rencana Implementasi

> **CATATAN SEJARAH — rencana ini SUDAH SELESAI dikerjakan.**
>
> Ketujuh tugasnya rampung 8-9 Agustus dan sudah tergabung ke `main`.
> Disimpan sebagai catatan bagaimana pekerjaan itu dipecah dan diuji,
> bukan sebagai daftar kerja. Beberapa keputusannya juga sudah dibalik
> sesudahnya — lihat catatan di kepala berkas spec di `../specs/`.

> **Untuk pekerja agentik:** SUB-SKILL WAJIB: pakai superpowers:subagent-driven-development (disarankan) atau superpowers:executing-plans untuk mengerjakan rencana ini tugas demi tugas. Langkahnya memakai kotak centang (`- [ ]`) untuk penanda.

**Tujuan:** Membuat karakter di kartu utama terbaca tajam dan menggigit seperti hasil edit Free Fire di TikTok, dengan menaikkan resolusi kutout memakai Real-ESRGAN lalu memenangkannya atas latar.

**Arsitektur:** Tiga fungsi penolong baru di `mesin/poster.py`, masing-masing satu tugas, dipanggil berurutan oleh `rakit()`. Biner upscaler diunduh sendiri oleh mesin dengan sidik jari SHA-256 yang dipatok, disimpan di `mesin/upscaler/` dan tidak masuk git. Jalur `poster.png` buatan Gemini tidak tersentuh karena `rakit()` memang hanya dipanggil ketika akun tidak punya berkas itu.

**Tumpukan teknologi:** Python 3 + Pillow (`ImageFilter`, `ImageEnhance`), `urllib.request`, `hashlib`, `zipfile`, biner `realesrgan-ncnn-vulkan` (ncnn + Vulkan lewat Metal).

## Batasan Global

- Semua nama fungsi, variabel, konstanta, komentar, docstring, dan pesan galat ditulis dalam bahasa Indonesia, mengikuti kode yang sudah ada.
- Pemeriksa memakai idiom repo ini: dekorator `@periksa('nama cek')` di atas `def _():` berisi `assert` biasa. Bukan pytest.
- Perintah menjalankan seluruh pemeriksa: `python3 mesin/uji_rakit.py`. Harus melaporkan semua lulus sebelum tugas dianggap selesai.
- Konstanta modul ditulis dengan komentar yang menjelaskan **kenapa** nilainya begitu, mengikuti gaya `TINGGI_KARAKTER` dan `KIKIS_PIKSEL` yang sudah ada.
- Nilai rasa yang dipatok spec, jangan diubah tanpa alasan tertulis:
  `UPSCALE_MODEL = 'realesr-animevideov3'`, `UPSCALE_SKALA = 4`,
  `LATAR_BLUR = 7`, `LATAR_REDUP = 0.88`, `STRUKTUR = (28, 60)`,
  `UNSHARP = (2.5, 130, 3)`, `KONTRAS = 1.14`, `SATURASI = 1.20`.
- Sidik jari arsip upscaler yang dipatok:
  `e0ad05580abfeb25f8d8fb55aaf7bedf552c375b5b4d9bd3c8d59764d2cc333a`
- Alamat arsip: `https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-macos.zip`
- Tiga anggota arsip yang diekstrak, namanya persis begini:
  `realesrgan-ncnn-vulkan`, `models/realesr-animevideov3-x4.bin`,
  `models/realesr-animevideov3-x4.param`
- Commit memakai gaya repo: `feat(materi-akun): ...`, `test(materi-akun): ...`, badan pesan menjelaskan sebab, bukan daftar perubahan.

## Peta Berkas

| Berkas | Tanggung jawab | Tugas |
|---|---|---|
| `mesin/uji_rakit.py` | Pemeriksa; ditambah mekanisme `Lewat` dan semua cek baru | 1–7 |
| `mesin/poster.py` | Tiga penolong baru + pemanggilannya di `rakit()` | 2–5 |
| `mesin/antrean.py` | Peringatan karakter kembar | 6 |
| `.gitignore` | Menahan `mesin/upscaler/` keluar dari git | 4 |
| `BACA-DULU.md` | Menjelaskan unduhan sekali-jalan dan arti peringatan baru | 7 |

---

### Tugas 1: Mekanisme "lewat" di pemeriksa

Cek yang membutuhkan biner upscaler tidak boleh melaporkan MERAH di salinan repo
yang belum pernah mengunduhnya. Tanpa ini, tugas-tugas berikutnya terpaksa
memilih antara cek yang rapuh atau tidak ada cek sama sekali.

**Berkas:**
- Modify: `mesin/uji_rakit.py` (kelas galat baru dekat `PERIKSAAN`, dan `_jalankan` di baris 1179)

**Antarmuka:**
- Consumes: —
- Produces: `class Lewat(Exception)` — cek yang melemparnya dilaporkan `lewat` dan **tidak** dihitung gagal. `_jalankan(periksaan)` tetap mengembalikan jumlah gagal.

- [ ] **Langkah 1: Tulis cek yang gagal**

Tambahkan tepat di bawah cek bernama `'cek yang meledak dengan exception non-AssertionError dilaporkan gagal, cek lain tetap jalan, total tetap tercetak'`:

```python
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
    assert 'lewat' in keluaran, f'tidak ada penanda lewat di keluaran:\n{keluaran}'
    assert 'biner upscaler belum diunduh' in keluaran, \
        'alasan melewati tidak ikut tercetak, jadi pemilik tidak tahu apa yang kurang'
    assert '2/2 lulus' not in keluaran, \
        'yang dilewati ikut dihitung lulus — itu menyesatkan, ia tidak diuji'
```

- [ ] **Langkah 2: Jalankan, pastikan merah**

Jalankan: `python3 mesin/uji_rakit.py`
Diharapkan: GAGAL dengan `[NameError] name 'Lewat' is not defined`

- [ ] **Langkah 3: Implementasi seminimalnya**

Tambahkan tepat di bawah `PERIKSAAN = []`:

```python
class Lewat(Exception):
    """Cek ini tidak bisa dijalankan di mesin ini, dan itu bukan kegagalan.

    Dipakai oleh cek yang butuh biner upscaler. Biner itu diunduh saat
    dibutuhkan dan sengaja tidak masuk git, jadi salinan repo yang masih
    bersih tidak memilikinya. Melaporkannya MERAH akan melatih pembaca
    mengabaikan warna merah — yang jauh lebih mahal daripada satu cek yang
    jujur mengaku tidak dijalankan.
    """
```

Lalu di `_jalankan`, sisipkan penangkap `Lewat` **sebelum** penangkap
`AssertionError` (urutan penting: `Lewat` bukan turunan `AssertionError`, tapi
menaruhnya lebih dulu membuat urutan bacanya sejalan dengan urutan prioritas):

```python
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
```

- [ ] **Langkah 4: Jalankan, pastikan hijau**

Jalankan: `python3 mesin/uji_rakit.py`
Diharapkan: semua lulus, 65 cek

- [ ] **Langkah 5: Commit**

```bash
git add mesin/uji_rakit.py
git commit -m "$(cat <<'PESAN'
test(materi-akun): pemeriksa bisa mengaku melewati cek, bukan memerahkannya

Cek yang butuh biner upscaler tidak bisa jalan di salinan repo yang belum
mengunduhnya. Melaporkannya MERAH melatih pembaca mengabaikan warna merah, dan
itu jauh lebih mahal daripada satu baris yang jujur mengaku tidak dijalankan.

Yang dilewati juga dikeluarkan dari penyebut, supaya "64/64 lulus" tidak pernah
berarti "64 hal terbukti" padahal sebagian tidak pernah disentuh.
PESAN
)"
```

---

### Tugas 2: `_perlakukan_latar` dan pemasangannya

**Berkas:**
- Modify: `mesin/poster.py` (konstanta baru; fungsi baru; `rakit()` di baris 109 dan 145)
- Modify: `mesin/uji_rakit.py` (dua cek baru)

**Antarmuka:**
- Consumes: `Lewat` dari Tugas 1 (belum dipakai di sini)
- Produces: `poster._perlakukan_latar(im: Image.Image) -> Image.Image` — RGBA masuk, RGBA keluar dengan ukuran sama; `poster.LATAR_BLUR = 7`; `poster.LATAR_REDUP = 0.88`

- [ ] **Langkah 1: Tulis cek yang gagal**

Tambahkan di `mesin/uji_rakit.py`, di dekat cek poster lain. Tambahkan juga
`import poster` di kelompok impor bagian atas kalau belum ada, dan
`from PIL import Image, ImageDraw, ImageFilter`:

```python
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
```

- [ ] **Langkah 2: Jalankan, pastikan merah**

Jalankan: `python3 mesin/uji_rakit.py`
Diharapkan: dua GAGAL dengan `[AttributeError] module 'poster' has no attribute '_perlakukan_latar'`

- [ ] **Langkah 3: Implementasi seminimalnya**

Di `mesin/poster.py`, tambahkan `ImageEnhance` ke impor Pillow:

```python
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
```

Tambahkan konstanta di bawah `KIKIS_PIKSEL`:

```python
# Latar diblur dan diredupkan bukan demi gaya, tapi karena mata menilai
# ketajaman secara relatif. Latar foto beresolusi penuh membuat karakter yang
# piksel aslinya cuma 226x570 selalu terbaca burik di sebelahnya, berapa pun
# angka pembesarannya. Menghentikan perbandingan itu memberi perbaikan lebih
# besar daripada mempertajam karakternya. Diukur 8 Agu 2026 pada bahan 666.
LATAR_BLUR = 7        # piksel, pada kanvas 2353 x 2521
LATAR_REDUP = 0.88    # 0,80 membuat lokasi latar hilang jadi lumpur
```

Tambahkan fungsi di bawah `_kikis_pinggiran`:

```python
def _perlakukan_latar(im: Image.Image) -> Image.Image:
    """Blur lalu redupkan latar supaya ia berhenti bersaing dengan karakter."""
    kabur = im.filter(ImageFilter.GaussianBlur(LATAR_BLUR))
    redup = ImageEnhance.Brightness(kabur.convert('RGB')).enhance(LATAR_REDUP)
    return redup.convert('RGBA')
```

Di `rakit()`, ganti baris 109 `latar = Image.open(berkas_latar).convert('RGBA')` menjadi:

```python
    # Perlakuan latar HARUS sebelum bayangan kaki digambar. Kalau sesudah,
    # bayangannya ikut terblur dua kali dan kaki kehilangan pijakan.
    latar = _perlakukan_latar(Image.open(berkas_latar).convert('RGBA'))
```

- [ ] **Langkah 4: Jalankan, pastikan hijau**

Jalankan: `python3 mesin/uji_rakit.py`
Diharapkan: semua lulus, 67 cek

- [ ] **Langkah 5: Commit**

```bash
git add mesin/poster.py mesin/uji_rakit.py
git commit -m "$(cat <<'PESAN'
feat(materi-akun): latar poster mundur supaya karakter jadi subjek

Mata menilai ketajaman dengan membandingkan. Latar foto beresolusi penuh
membuat karakter yang piksel aslinya cuma 226x570 selalu terbaca burik di
sebelahnya, walau mesin cuma membesarkannya 1,1x.

Memblur dan meredupkan latar menghentikan perbandingan itu, dan pada uji
berdampingan ia memberi perbaikan lebih besar daripada mempertajam karakternya.
Urutannya mengikat: latar diperlakukan sebelum bayangan kaki digambar, kalau
tidak bayangannya terblur dua kali dan kaki kehilangan pijakan.
PESAN
)"
```

---

### Tugas 3: `_perlakukan_karakter` dan pemasangannya

**Berkas:**
- Modify: `mesin/poster.py` (konstanta baru; fungsi baru; `rakit()` di baris 150–152)
- Modify: `mesin/uji_rakit.py` (tiga cek baru)

**Antarmuka:**
- Consumes: `_energi_tepi` dari Tugas 2
- Produces: `poster._perlakukan_karakter(im: Image.Image) -> Image.Image` — RGBA masuk, RGBA keluar, ukuran sama, kanal alfa identik; `poster.STRUKTUR`, `poster.UNSHARP`, `poster.KONTRAS`, `poster.SATURASI`

- [ ] **Langkah 1: Tulis cek yang gagal**

```python
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
    asal = _kutout_uji()
    hasil = poster._perlakukan_karakter(asal)

    def _rentang_warna(im):
        # Selisih kanal per piksel = ukuran kasar seberapa berwarna gambarnya.
        r, g, b = (list(im.convert('RGB').getchannel(k).getdata()) for k in range(3))
        return sum(max(a, c, d) - min(a, c, d) for a, c, d in zip(r, g, b)) / len(r)

    assert _rentang_warna(hasil) > _rentang_warna(asal), \
        'warna tidak jadi lebih pekat — SATURASI tidak berlaku'
```

- [ ] **Langkah 2: Jalankan, pastikan merah**

Jalankan: `python3 mesin/uji_rakit.py`
Diharapkan: tiga GAGAL dengan `[AttributeError] module 'poster' has no attribute '_perlakukan_karakter'`

- [ ] **Langkah 3: Implementasi seminimalnya**

Konstanta baru di `mesin/poster.py`, di bawah `LATAR_REDUP`:

```python
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
```

Fungsi baru di bawah `_perlakukan_latar`:

```python
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
```

Di `rakit()`, ganti blok penempelan (baris 148–152) menjadi:

```python
        # Kiri dan kanan dulu, tengah paling akhir supaya tumpang tindih di depan.
        for i in (0, 2, 1):
            x, y, lebar, tinggi = tempat[i]
            # Diperlakukan SETELAH diskalakan ke ukuran tayang. Mempertajam
            # sebelum resize sia-sia: resampling membubarkan lagi hasilnya.
            p = potongan[i].crop(kotak_alfa[i]).resize(
                (lebar, tinggi), Image.Resampling.LANCZOS)
            p = _perlakukan_karakter(p)
            latar.paste(p, (x, y), p)
```

- [ ] **Langkah 4: Jalankan, pastikan hijau**

Jalankan: `python3 mesin/uji_rakit.py`
Diharapkan: semua lulus, 70 cek

- [ ] **Langkah 5: Commit**

```bash
git add mesin/poster.py mesin/uji_rakit.py
git commit -m "$(cat <<'PESAN'
feat(materi-akun): karakter poster diangkat dengan structure dan sharpen

Structure dan sharpen bukan pengulangan. Radius besar berkadar sedang
mengangkat tekstur kain dan ukiran senjata tanpa menyentuh tepi siluet; radius
kecil berkadar tinggi menegaskan tepinya. Memakai sharpen saja terbukti kurang
berisi saat diadu berdampingan.

Perlakuan dijalankan setelah kutout diskalakan ke ukuran tayang, karena
mempertajam sebelum resize akan dibubarkan lagi oleh resampling. Kanal alfa
dipisah dan dikembalikan utuh supaya tepinya tidak melahirkan halo.
PESAN
)"
```

---

### Tugas 4: Pengambil biner upscaler

Bagian paling berisiko dari seluruh rancangan: mesin mengeksekusi kode yang baru
diunduh. Ia dikerjakan sebagai tugas tersendiri supaya verifikasinya diuji utuh
sebelum ada yang memanggilnya.

**Berkas:**
- Modify: `mesin/poster.py` (konstanta + dua fungsi baru)
- Modify: `mesin/uji_rakit.py` (tiga cek baru)
- Modify: `.gitignore`

**Antarmuka:**
- Consumes: `Lewat` dari Tugas 1
- Produces: `poster._ambil_upscaler() -> Tuple[Path, Path]` mengembalikan `(biner, folder_model)`, mengunduh kalau perlu; `poster._periksa_sidik(arsip: Path) -> None` melempar `RuntimeError` kalau sha256 tidak cocok; `poster.UPSCALE_DIR`, `poster.UPSCALE_URL`, `poster.UPSCALE_SHA256`

- [ ] **Langkah 1: Tulis cek yang gagal**

```python
@periksa('arsip upscaler bersidik jari salah ditolak, tidak diekstrak, tidak dijalankan')
def _():
    with tempfile.TemporaryDirectory() as t:
        palsu = Path(t) / 'palsu.zip'
        palsu.write_bytes(b'ini bukan arsip Real-ESRGAN')
        try:
            poster._periksa_sidik(palsu)
        except RuntimeError as e:
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


@periksa('unduhan gagal BERHENTI menyebut sebabnya, tidak mundur diam-diam')
def _():
    asli_url = poster.UPSCALE_URL
    asli_dir = poster.UPSCALE_DIR
    with tempfile.TemporaryDirectory() as t:
        poster.UPSCALE_URL = 'https://127.0.0.1:1/tidak-ada.zip'
        poster.UPSCALE_DIR = Path(t) / 'upscaler'
        try:
            poster._ambil_upscaler()
        except RuntimeError as e:
            assert 'jaringan' in str(e) or 'unduhan' in str(e), \
                f'pesan tidak menjelaskan bahwa sebabnya unduhan: {e}'
        else:
            raise AssertionError(
                'unduhan gagal malah lolos — mesin akan menghasilkan kartu '
                'yang dikira sudah HD padahal tidak')
        finally:
            poster.UPSCALE_URL = asli_url
            poster.UPSCALE_DIR = asli_dir
```

Tambahkan `import hashlib` di kelompok impor `mesin/uji_rakit.py`.

- [ ] **Langkah 2: Jalankan, pastikan merah**

Jalankan: `python3 mesin/uji_rakit.py`
Diharapkan: tiga GAGAL dengan `[AttributeError] module 'poster' has no attribute '_periksa_sidik'`

- [ ] **Langkah 3: Implementasi seminimalnya**

Impor tambahan di `mesin/poster.py`:

```python
import hashlib
import shutil
import urllib.error
import urllib.request
import zipfile
```

Konstanta di bawah `LATAR_BAWAAN`:

```python
UPSCALE_DIR = Path(__file__).parent / 'upscaler'
UPSCALE_URL = ('https://github.com/xinntao/Real-ESRGAN/releases/download/'
               'v0.2.5.0/realesrgan-ncnn-vulkan-20220424-macos.zip')
UPSCALE_SHA256 = 'e0ad05580abfeb25f8d8fb55aaf7bedf552c375b5b4d9bd3c8d59764d2cc333a'
UPSCALE_MODEL = 'realesr-animevideov3'
UPSCALE_SKALA = 4
# Hanya tiga dari enam belas anggota arsip yang dipakai. Sembilan model lain
# tidak diekstrak: 50MB berkas yang tidak pernah dibuka.
_ANGGOTA = ('realesrgan-ncnn-vulkan',
            f'models/{UPSCALE_MODEL}-x{UPSCALE_SKALA}.bin',
            f'models/{UPSCALE_MODEL}-x{UPSCALE_SKALA}.param')
```

Dua fungsi baru:

```python
def _periksa_sidik(arsip: Path) -> None:
    """Bandingkan sha256 arsip dengan yang dipatok. Melempar kalau berbeda.

    Mesin akan MENJALANKAN isi arsip ini, jadi berkas yang tidak dikenal tidak
    boleh pernah diekstrak, apalagi dieksekusi.
    """
    sidik = hashlib.sha256(arsip.read_bytes()).hexdigest()
    if sidik != UPSCALE_SHA256:
        raise RuntimeError(
            f'sidik jari arsip upscaler tidak cocok.\n'
            f'  diharapkan: {UPSCALE_SHA256}\n'
            f'  didapat   : {sidik}\n'
            f'Berkasnya tidak dijalankan dan tidak diekstrak.')


def _ambil_upscaler():
    """Kembalikan (biner, folder_model), mengunduh sekali kalau belum ada."""
    biner = UPSCALE_DIR / 'realesrgan-ncnn-vulkan'
    model = UPSCALE_DIR / 'models'
    if biner.exists() and (model / f'{UPSCALE_MODEL}-x{UPSCALE_SKALA}.bin').exists():
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
            raise RuntimeError(
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
    subprocess.run(['xattr', '-dr', 'com.apple.quarantine', str(UPSCALE_DIR)],
                   capture_output=True)
    print('  upscaler siap')
    return biner, model
```

Tambahkan ke `.gitignore`:

```
mesin/upscaler/
```

- [ ] **Langkah 4: Jalankan, pastikan hijau**

Jalankan: `python3 mesin/uji_rakit.py`
Diharapkan: semua lulus, 73 cek

- [ ] **Langkah 5: Buktikan unduhan sungguhan bekerja**

Jalankan: `python3 -c "import sys; sys.path.insert(0,'mesin'); import poster; print(poster._ambil_upscaler())"`
Diharapkan: mencetak baris "mengambil upscaler", lalu "upscaler siap", lalu pasangan path. Jalankan sekali lagi — kali kedua harus langsung mencetak path tanpa mengunduh.

Lalu buktikan ekstraksinya selektif:

```bash
ls mesin/upscaler/models/
```
Diharapkan: tepat dua berkas, `realesr-animevideov3-x4.bin` dan `.param`. Tidak ada `x4plus`.

- [ ] **Langkah 6: Commit**

```bash
git add mesin/poster.py mesin/uji_rakit.py .gitignore
git commit -m "$(cat <<'PESAN'
feat(materi-akun): mesin mengambil sendiri biner upscaler, dengan sidik jari dipatok

Biner Real-ESRGAN tidak bisa dikompilasi dari sumber seperti potong, jadi ia
diunduh saat pertama dibutuhkan. Karena mesin akan MENJALANKAN isi arsip itu,
sha256-nya dipatok: arsip yang sidik jarinya tidak cocok tidak pernah diekstrak,
apalagi dieksekusi.

Unduhan yang gagal menghentikan proses sambil menyebut sebabnya, bukan mundur
diam-diam ke jalur lama — mundur diam-diam berarti pemilik mengunggah kartu yang
dikira sudah HD padahal tidak.

Tiga dari enam belas anggota arsip yang diekstrak; sembilan model lain adalah
50MB yang tidak pernah dibuka.
PESAN
)"
```

---

### Tugas 5: `_naikkan_resolusi` dan pemasangannya

**Berkas:**
- Modify: `mesin/poster.py` (fungsi baru; `rakit()` di baris 111–113)
- Modify: `mesin/uji_rakit.py` (empat cek baru)

**Antarmuka:**
- Consumes: `poster._ambil_upscaler()` dari Tugas 4; `Lewat` dari Tugas 1
- Produces: `poster._naikkan_resolusi(im: Image.Image, tinggi_tayang: int) -> Image.Image`

- [ ] **Langkah 1: Tulis cek yang gagal**

```python
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

    def _porsi_transisi(im):
        h = im.getchannel('A').histogram()
        return sum(h[8:248]) / sum(h)

    nisbah = _porsi_transisi(hasil) / _porsi_transisi(asal)
    assert nisbah < 1.5, \
        (f'porsi piksel alfa separuh-tembus melonjak {nisbah:.2f}x — tepinya '
         f'jadi kabur dan akan lahir jadi halo')


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


@periksa('tata_letak kebal skala: kotak alfa 4x menghasilkan penempatan yang sama')
def _():
    kotak = [(0, 0, 226, 570)] * 3
    besar = [(0, 0, 904, 2280)] * 3
    assert poster.tata_letak((2353, 2521), kotak) == poster.tata_letak((2353, 2521), besar), \
        ('penempatan bergeser saat kutout di-upscale — upscale seharusnya '
         'mengubah piksel, bukan geometri')
```

- [ ] **Langkah 2: Jalankan, pastikan merah**

Jalankan: `python3 mesin/uji_rakit.py`
Diharapkan: GAGAL dengan `[AttributeError] module 'poster' has no attribute '_naikkan_resolusi'` (cek `tata_letak` sudah hijau sejak awal — ia menguji sifat yang memang sudah ada dan harus dijaga)

- [ ] **Langkah 3: Implementasi seminimalnya**

Fungsi baru di `mesin/poster.py`, di bawah `_ambil_upscaler`:

```python
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
```

Di `rakit()`, ganti baris 111–113 menjadi:

```python
    with tempfile.TemporaryDirectory() as t:
        # Tinggi tayang terbesar (karakter tengah) jadi patokan pelewatan.
        # Diturunkan dari konstanta tata letak, bukan ditulis ulang sebagai
        # angka kedua yang bisa berselisih diam-diam kalau tata letaknya disetel.
        tinggi_tayang = round(latar.height * TINGGI_KARAKTER * SKALA_TENGAH)
        # Upscale SESUDAH _kikis_pinggiran: KIKIS_PIKSEL dikalibrasi pada skala
        # sumber dan akan salah takaran pada gambar yang sudah membesar 4x.
        potongan = [_naikkan_resolusi(_potong(b, Path(t) / f'{i}.png'), tinggi_tayang)
                    for i, b in enumerate(akun.karakter)]
```

- [ ] **Langkah 4: Jalankan, pastikan hijau**

Jalankan: `python3 mesin/uji_rakit.py`
Diharapkan: semua lulus, 77 cek

- [ ] **Langkah 5: Buktikan pada bahan sungguhan**

```bash
python3 mesin/rakit.py antrean siap-upload
```
Diharapkan: selesai tanpa BERHENTI, dan `siap-upload/666-utama.webp` terbarui. Buka dan bandingkan dengan ingatan versi lama: karakter harus jauh lebih bersih, latar mundur.

- [ ] **Langkah 6: Commit**

```bash
git add mesin/poster.py mesin/uji_rakit.py
git commit -m "$(cat <<'PESAN'
feat(materi-akun): kutout karakter dinaikkan 4x sebelum ditempel

Free Fire me-render di resolusi rendah demi FPS, jadi kutout karakter cuma
226x570 piksel. Real-ESRGAN membalik arah rantai skala: yang tadinya DIBESARKAN
2,65x kini justru DIKECILKAN dari 2280px, dan mengecilkan selalu lebih bersih.

Ia juga membuang derau yang selama ini membatasi structure dan sharpen. Angka
rasa yang sama persis, yang tanpa upscale membuat sweter hitam berbintik, kini
menghasilkan kain bersih.

Upscale dilewati kalau kutoutnya sudah setinggi tayang — pada kutout 900x2270 ia
memakan 4,28 detik dan 131MB untuk 32,7 megapiksel yang seluruhnya dibuang lagi.
Itu bukan skenario khayalan: ia terjadi persis saat sumbernya naik lewat AirDrop.
PESAN
)"
```

---

### Tugas 6: Peringatan karakter kembar

**Berkas:**
- Modify: `mesin/antrean.py` (di `_periksa`, baris 168–204)
- Modify: `mesin/uji_rakit.py` (dua cek baru)

**Antarmuka:**
- Consumes: —
- Produces: `antrean.baca()` tetap mengembalikan `(akun, dilewati)`; akun dengan `karakter/` berisi berkas isi-identik kini menghasilkan satu baris PERINGATAN lewat jalur peringatan yang sudah dipakai `rakit.jalankan`

- [ ] **Langkah 1: Tulis cek yang gagal**

**Perhatikan jebakan di fixture.** `_buat_akun` (baris 109) menyimpan SEMUA
berkas karakter sebagai kotak merah 60×60 yang sama persis. Jadi akun bawaannya
sudah kembar, dan cek negatifnya harus menimpa berkasnya dengan gambar yang
benar-benar berbeda — kalau tidak, ia merah karena fixture, bukan karena kode.

```python
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
```

- [ ] **Langkah 2: Jalankan, pastikan merah**

Jalankan: `python3 mesin/uji_rakit.py`
Diharapkan: GAGAL dengan `[AttributeError] 'Akun' object has no attribute 'peringatan'`

- [ ] **Langkah 3: Implementasi seminimalnya**

Di `mesin/antrean.py`, tambahkan `import hashlib` dan tambahkan medan baru pada
`@dataclass class Akun` (baris 51):

```python
    peringatan: List[str] = field(default_factory=list)
```

Di `_periksa`, setelah `karakter` terkumpul dan sebelum `Akun(...)` dibentuk:

```python
    peringatan = []
    if len(karakter) > 1:
        # Berkas karakter yang isinya sama persis menghasilkan poster berisi
        # satu karakter yang dikloning tiga kali. Ini salah isi antrean, bukan
        # salah mesin — tapi tanpa peringatan, pemilik akan menyangka perlakuan
        # gambarnyalah yang gagal. Diukur 8 Agu 2026: ketiga berkas di 666
        # ternyata md5 identik, bernama copy dan copy 2.
        sidik = [hashlib.md5(b.read_bytes()).hexdigest() for b in karakter]
        if len(set(sidik)) < len(sidik):
            peringatan.append(
                'karakter/ berisi berkas yang isinya identik — posternya akan '
                'memajang karakter yang sama lebih dari sekali')
```

Lalu sertakan `peringatan=peringatan` pada pemanggilan `Akun(...)` di baris 203.

Terakhir, di `mesin/rakit.py`, tepat sebelum baris
`catat_potongan: List[str] = []` (baris 150), teruskan peringatan antrean ke
penampung yang sudah ada. Penampung itu berisi **pasangan** `(kode, pesan)`,
bukan teks polos, jadi bentuknya harus sama:

```python
            for pesan in akun.peringatan:
                peringatan_akun.append((akun.kode, pesan))
```

- [ ] **Langkah 4: Jalankan, pastikan hijau**

Jalankan: `python3 mesin/uji_rakit.py`
Diharapkan: semua lulus, 79 cek

- [ ] **Langkah 5: Buktikan pada bahan sungguhan**

```bash
python3 mesin/rakit.py antrean siap-upload
```
Diharapkan: muncul PERINGATAN yang menyebut `karakter/` identik untuk akun 666,
karena ketiga berkasnya memang md5 identik.

- [ ] **Langkah 6: Commit**

```bash
git add mesin/antrean.py mesin/rakit.py mesin/uji_rakit.py
git commit -m "$(cat <<'PESAN'
feat(materi-akun): karakter kembar diperingatkan, bukan dibiarkan lolos

Ketiga berkas di antrean/pelajar/666/karakter/ ternyata md5 identik — satu
screenshot yang digandakan dan diberi akhiran copy dan copy 2. Posternya memajang
karakter yang sama tiga kali, dan mesin tidak punya deteksi kembar sama sekali.

Ini salah isi antrean, bukan salah mesin. Tapi tanpa peringatan, pemilik akan
menjalankan ulang seusai semua perbaikan gambar, tetap melihat tiga kloning, dan
wajar menyimpulkan perlakuannyalah yang gagal.

PERINGATAN, bukan DILEWATI dan bukan BERHENTI: kartunya tetap dibuat, karena
pemilik yang berhak memutuskan apakah kembarnya memang disengaja.
PESAN
)"
```

---

### Tugas 7: Dokumentasi

**Berkas:**
- Modify: `BACA-DULU.md`

**Antarmuka:**
- Consumes: perilaku yang dibangun Tugas 1–6
- Produces: —

- [ ] **Langkah 1: Tambahkan bagian tentang unduhan sekali-jalan**

Sisipkan tepat sebelum bagian `## Kalau pemeriksanya merah`:

```markdown
## Lari pertama mengunduh sekali

Kali pertama kamu merakit poster dari `karakter/`, mesin mengambil biner
penaik-resolusi (± 52 MB) dari rilis resmi Real-ESRGAN. Ia mencetak barisnya,
jadi layar tidak akan diam tanpa penjelasan. Setelah itu ia tersimpan di
`mesin/upscaler/` dan tidak pernah diunduh lagi.

Arsipnya diperiksa sidik jarinya sebelum dipakai. Kalau tidak cocok, mesin
BERHENTI dan tidak menjalankan apa pun — itu disengaja.

Butuh jaringan hanya pada lari pertama itu. Kalau jaringan mati saat dibutuhkan,
mesin berhenti dan mengatakannya, bukan diam-diam menghasilkan kartu yang kamu
kira sudah HD.
```

- [ ] **Langkah 2: Tambahkan arti peringatan baru**

Di bagian `## Membaca hasilnya`, sesudah butir **PERINGATAN**, tambahkan:

```markdown
Salah satu peringatan yang mungkin muncul: `karakter/` berisi berkas yang isinya
identik. Artinya kamu menaruh satu screenshot yang sama beberapa kali — sering
terjadi kalau berkasnya digandakan jadi `copy` dan `copy 2`. Posternya tetap
dibuat, tapi akan memajang karakter yang sama lebih dari sekali.
```

- [ ] **Langkah 3: Perbarui bagian karakter**

Di bagian `## Dua cara memberi poster`, pada **Cara 1**, tambahkan di akhir alinea:

```markdown
Karakternya dinaikkan resolusinya empat kali lipat sebelum ditempel, jadi
screenshot lobi yang tampak buram di HP tetap terbaca tajam di kartu. Yang
dinaikkan cuma ketajamannya — senjata, skin, dan pose tetap yang kamu potret.
```

- [ ] **Langkah 4: Periksa dokumen tidak berbohong**

Jalankan: `python3 mesin/uji_rakit.py`
Diharapkan: semua lulus. Lalu baca ulang bagian yang kamu tambahkan dan cocokkan
tiap klaimnya dengan perilaku yang benar-benar dibangun di Tugas 1–6.

- [ ] **Langkah 5: Commit**

```bash
git add BACA-DULU.md
git commit -m "$(cat <<'PESAN'
docs(materi-akun): jelaskan unduhan sekali-jalan dan peringatan karakter kembar

Lari pertama mengambil biner penaik-resolusi 52MB. Pemilik yang tidak tahu itu
akan mengira perkakasnya macet, jadi BACA-DULU menyebutkannya sekarang, berikut
apa yang terjadi kalau sidik jarinya tidak cocok atau jaringan mati.
PESAN
)"
```

---

## Tinjauan Mandiri

**Cakupan spec:** Ketiga belas uji di spec punya tugasnya. Uji 1 → Tugas 3;
uji 2 → Tugas 2; uji 3 → Tugas 3; uji 4 → Tugas 5 (dijadikan cek kekebalan skala
`tata_letak`, yang menguji sifat sebenarnya alih-alih tautologi); uji 5 → Tugas 5
lewat cek pelewatan yang membuktikan biner tidak dipanggil; uji 6 → Tugas 6;
uji 7–10 → Tugas 5; uji 11–13 → Tugas 4. Pemecahan fungsi → Tugas 2, 3, 5.
Baris unduhan bersuara → Tugas 4. Dokumentasi → Tugas 7.

**Satu penyimpangan sadar dari spec:** spec menyebut uji "jalur Gemini bersih"
dibuktikan dengan mengganti penolong oleh versi yang meledak. Rencana ini
membuktikannya lewat jalur yang lebih langsung — `rakit()` memang tidak pernah
dipanggil untuk akun berposter, dan itu sudah dijamin cek `_poster_untuk` yang
ada. Menambah cek yang menyabot penolong hanya akan menguji ulang percabangan
yang sudah terjaga.

**Ketergantungan antar tugas:** Tugas 1 harus lebih dulu (menyediakan `Lewat`).
Tugas 4 harus mendahului Tugas 5 (menyediakan `_ambil_upscaler`). Tugas 2, 3,
dan 6 saling bebas. Tugas 7 paling akhir.
