# Perakit Materi Listing Akun

Satu klik mengubah screenshot mentah dari game jadi kartu siap unggah ke `/akun-admin`.

> **Panduan ini untuk Windows.** Kamu cuma perlu bisa copy-paste dan klik dua kali.
> Detail teknis lengkap (termasuk cara macOS) ada di [BACA-DULU.md](BACA-DULU.md).

---

## Persiapan (sekali saja)

### 1. Pasang Python

1. Buka <https://www.python.org/downloads/> → klik tombol kuning **Download Python**.
2. Jalankan pemasangnya. ⚠️ **Centang "Add python.exe to PATH"** di layar pertama,
   baru klik *Install Now*. Kalau lupa, ulangi pemasangan dari awal.
3. Cek: buka **Command Prompt** (tombol Windows → ketik `cmd` → Enter), lalu:

   ```
   python --version
   ```

   Keluar angka versi (misal `Python 3.14.0`) = berhasil.

### 2. Pasang Pillow

Masih di Command Prompt:

```
pip install pillow
```

### 3. Ambil repo ini

Klik tombol hijau **Code → Download ZIP** di atas, ekstrak di mana saja.
(Atau `git clone` kalau sudah biasa.)

---

## Pemakaian sehari-hari

### 1. Isi antrean

Di folder `antrean\` ada tiga tingkat. Nama folder menentukan label di kartu:

| Folder | Tercetak di kartu |
|---|---|
| `antrean\pelajar\` | Pelajar |
| `antrean\reguler\` | Reguler |
| `antrean\premium\` | Sultan |

Untuk tiap akun, bikin **satu folder baru** di tingkat yang sesuai.
**Nama folder = kode akun** yang tercetak di kartu. Isinya:

```
antrean\pelajar\6001\
  poster.png        ← WAJIB. Poster jadi, ukuran ± 2353 × 2521
  fashion.png       ← 1 screenshot layar Fashion (nama bebas)
  slide\            ← screenshot bukti dari game, jumlah HARUS GENAP
  item\             ← bikin foldernya, biarkan kosong
  info.txt          ← satu baris: harga: 750.000
```

Sudah ada contoh jadi di `antrean\` — **tinggal tiru strukturnya**.

Rincian tiap berkas:

- **poster.png** — di Windows wajib ada. Minta dibuatkan di Gemini, sebut
  ukurannya **± 2353 × 2521**. Tanpa berkas ini proses berhenti dengan pesan
  `BERHENTI:` — disengaja, bukan rusak.
- **fashion.png** — screenshot layar Fashion. Ikon item dipotong otomatis dari
  sini. ⚠️ Jangan taruh dua gambar di akar folder akun — mesin bingung dan akun
  itu dilewati.
- **slide\\** — screenshot layar Vault / Collection / apa pun yang memperlihatkan
  skin. Tiap **2 berkas jadi 1 kartu**, jadi isinya 2, 4, atau 6.
- **info.txt** — bikin lewat Notepad:

  ```
  harga: 750.000
  item: 3 4 6 7
  ```

  Baris `item:` opsional — nomor petak layar Fashion dihitung dari atas, urutannya
  = urutan slot di kartu. Tanpa baris itu, empat petak pertama yang diambil.

### 2. Jalankan

**Klik dua kali `jalankan.bat`.** Itu saja. Selesai → folder `siap-upload\`
terbuka sendiri.

### 3. Baca hasilnya

Jendela hitam mencetak empat daftar:

| Daftar | Artinya |
|---|---|
| **berkas dibuat** | Sukses — kartu ada di `siap-upload\` |
| **akun sudah ada** | Sudah pernah dirakit, tidak dibuat ulang |
| **PERINGATAN** | Kartu jadi, tapi periksa dulu sebelum dipakai |
| **folder DILEWATI** | Tidak jadi — alasannya tercetak, perbaiki lalu jalankan lagi |

Muncul **`BERHENTI:`** = ada salah pasang (akun tanpa `poster.png`, nama tingkat
keliru, kode akun kembar). Baca pesannya, betulkan, klik `jalankan.bat` lagi.

### 4. Unggah

Tiap akun punya folder sendiri di `siap-upload\`:

```
siap-upload\FF-PELAJAR-6001\
  FF-PELAJAR-6001-utama.webp     ← Foto #1, jadi thumbnail
  FF-PELAJAR-6001-slide-1.webp   ← Foto #2 dan seterusnya
  FF-PELAJAR-6001-slide-2.webp
```

Buka satu folder → unggah semua isinya ke `/akun-admin` urut dari `-utama` →
tutup → lanjut folder berikutnya.

---

## Sering ditanya

**Mau merakit ulang satu akun?**
Hapus foldernya di `siap-upload\`, klik `jalankan.bat` lagi. Mengubah isi
`antrean\` saja tidak cukup — mesin cuma melihat folder keluaran.

**Merakit ulang semuanya?**
Command Prompt dari folder repo: `python mesin\rakit.py antrean siap-upload --ulang`

**Jendela hitam menutup seketika?**
Python belum terpasang benar — ulangi Persiapan langkah 1.

**Kenapa tidak bisa pakai folder `karakter\` seperti di macOS?**
Pemotong karakter memakai Vision, bawaan macOS, tidak ada di Windows. Di sini
semua akun wajib bawa `poster.png`. Selain itu semuanya identik.

**Cek kesehatan mesin:**
`python mesin\uji_rakit.py` — di Windows dua cek `potong ...` tampil **lewat**,
itu normal. Yang **merah** berarti benar-benar rusak.
