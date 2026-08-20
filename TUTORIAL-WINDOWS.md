# Tutorial Windows — buat yang baru pertama kali

Panduan ini buat kamu yang cuma mau **menjalankan** perkakasnya di Windows.
Tidak perlu paham kode. Ikuti urut dari atas.

## 1. Pasang Python (sekali saja)

1. Buka <https://www.python.org/downloads/> lalu klik tombol kuning **Download Python**.
2. Jalankan pemasangnya. **PENTING:** centang kotak **"Add python.exe to PATH"**
   di layar pertama sebelum klik Install Now. Kalau lupa dicentang, ulangi
   pemasangannya dari awal — lebih cepat daripada membetulkan PATH manual.
3. Setelah selesai, buka **Command Prompt** (tekan tombol Windows, ketik `cmd`,
   Enter) lalu ketik:

   ```
   python --version
   ```

   Kalau keluar angka versi (misal `Python 3.14.0`), berhasil.

## 2. Pasang Pillow (sekali saja)

Masih di Command Prompt:

```
pip install pillow
```

Tunggu sampai selesai. Sudah, tutup jendelanya.

## 3. Isi antrean

Buka folder repo ini di Explorer. Di dalamnya ada folder `antrean\` dengan tiga
subfolder:

| Folder | Yang tercetak di kartu |
|---|---|
| `antrean\pelajar\` | Pelajar |
| `antrean\reguler\` | Reguler |
| `antrean\premium\` | Sultan |

Untuk tiap akun yang mau dibuatkan kartu, bikin **satu folder baru** di dalam
tingkat yang sesuai. **Nama foldernya = kode akun** yang akan tercetak di kartu.

Isi folder akun seperti ini:

```
antrean\pelajar\6001\
  poster.png        <- WAJIB. Poster jadi, ukuran sekitar 2353 x 2521
  fashion.png       <- 1 screenshot layar Fashion (namanya bebas)
  slide\            <- screenshot mentah dari game, jumlahnya HARUS GENAP
  item\             <- bikin foldernya, biarkan kosong
  info.txt          <- isi satu baris: harga: 750.000
```

Penjelasan singkat:

- **poster.png** — di Windows ini wajib ada. Minta dibuatkan di Gemini,
  sebut ukurannya sekitar **2353 x 2521**. Tanpa berkas ini prosesnya berhenti
  dengan pesan `BERHENTI:` — itu disengaja, bukan rusak.
- **fashion.png** — screenshot layar Fashion dari game. Ikon item dipotong
  otomatis dari sini. **Jangan taruh dua gambar di akar folder akun** — mesin
  bingung mana yang layar Fashion, dan akun itu dilewati.
- **slide\\** — screenshot bukti buat pembeli: layar Vault, Collection, apa pun
  yang memperlihatkan skin. Tiap **2 berkas jadi 1 kartu**, jadi isinya harus
  genap: 2, 4, atau 6 berkas.
- **info.txt** — bikin lewat Notepad. Isinya minimal satu baris:

  ```
  harga: 750.000
  ```

  Mau memilih sendiri ikon item yang tampil? Tambah baris kedua, angkanya nomor
  petak di layar Fashion dihitung dari atas:

  ```
  item: 3 4 6 7
  ```

  Tanpa baris itu, empat petak pertama yang diambil.

## 4. Jalankan

**Klik dua kali `jalankan.bat`.** Itu saja.

Jendela hitam terbuka dan mesin bekerja. Setelah selesai, folder `siap-upload\`
terbuka sendiri.

## 5. Baca hasilnya

Di jendela hitam, mesin mencetak empat daftar:

- **berkas dibuat** — sukses, kartunya ada di `siap-upload\`
- **akun sudah ada** — sudah pernah dirakit sebelumnya, tidak dibuat ulang
- **PERINGATAN** — kartunya jadi, tapi periksa dulu sebelum dipakai
- **folder DILEWATI** — tidak jadi, alasannya tercetak; perbaiki lalu jalankan lagi

Kalau muncul **`BERHENTI:`** artinya ada yang salah pasang (misal ada akun tanpa
`poster.png`, atau nama tingkatnya keliru). Baca pesannya — di situ tertulis apa
yang harus dibetulkan. Betulkan, lalu klik `jalankan.bat` lagi.

## 6. Ambil dan unggah

Tiap akun punya foldernya sendiri di `siap-upload\`, dinamai kodenya:

```
siap-upload\FF-PELAJAR-6001\
  FF-PELAJAR-6001-utama.webp     <- Foto #1, jadi thumbnail
  FF-PELAJAR-6001-slide-1.webp   <- Foto #2 dan seterusnya
  FF-PELAJAR-6001-slide-2.webp
```

Buka satu folder, unggah semua isinya ke `/akun-admin` urut dari `-utama`, tutup,
lanjut folder berikutnya.

## Pertanyaan yang sering muncul

**Mau merakit ulang satu akun yang sudah jadi?**
Hapus foldernya di `siap-upload\`, lalu klik `jalankan.bat` lagi. Mengganti
isi `antrean\` saja tidak cukup — mesin cuma melihat folder keluaran.

**Jendela hitamnya menutup sendiri sebelum sempat dibaca?**
Tidak akan — ada `pause` di akhir. Kalau menutup seketika, Python-nya belum
terpasang benar; ulangi langkah 1.

**Kenapa tidak bisa pakai folder `karakter\` seperti di macOS?**
Pemotong karakternya memakai Vision, bawaan macOS, dan tidak ada di Windows.
Di sini semua akun wajib bawa `poster.png`. Selain itu semuanya sama.

**Muncul cek merah waktu menjalankan `python mesin\uji_rakit.py`?**
Dua cek berlabel `potong ...` tampil sebagai **lewat** di Windows — itu normal.
Yang **merah** berarti benar-benar ada yang rusak; tanyakan ke yang pasang.
