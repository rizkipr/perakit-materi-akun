# Perakit materi listing akun

Satu perintah mengubah screenshot mentah jadi kartu siap unggah ke `/akun-admin`.

## Yang perlu terpasang

Python 3 dan Pillow. Sekali saja:

```bash
pip install pillow
```

## Cara pakai

**Di macOS: klik dua kali `jalankan.command`. Di Windows: `jalankan.bat`.** Selesai.

Atau lewat Terminal, dari akar repo:

```bash
python3 mesin/rakit.py antrean siap-upload
```

Di Windows, perintahnya `python`, bukan `python3`:

```bash
python mesin\rakit.py antrean siap-upload
```

**Yang sudah jadi tidak dibuat ulang.** Akun yang sudah punya kartu di
`siap-upload/<kode>/` dilewati, jadi menambah satu akun baru ke antrean cuma
merakit yang baru itu. Mereka tercetak di ringkasan dengan bagiannya sendiri,
bukan sebagai `DILEWATI` — tidak ada yang perlu kamu perbaiki.

Mau merakit ulang satu akun? Hapus foldernya di `siap-upload`, lalu jalankan
lagi. Mau semuanya?

```bash
python3 mesin/rakit.py antrean siap-upload --ulang
```

Yang diperiksa cuma folder keluarannya. Mengganti screenshot di `antrean/`
**tidak** membuat kartunya dibuat ulang sendiri, begitu juga menyetel mesin atau
mengganti isi `latar/` — hapus foldernya atau pakai `--ulang`.

## Isi folder ini

| Folder | Untuk apa |
|---|---|
| `antrean/` | **Kamu isi di sini.** Satu folder per akun |
| `siap-upload/` | **Kamu ambil dari sini.** Satu folder per akun, unggah ke `/akun-admin` |
| `latar/` | Latar poster per tingkat. Ganti kalau mau ganti suasana |
| `mesin/` | Kode dan asetnya. Jangan disentuh |
| `template-master.psd` | Berkas Photoshop asli. Untuk menyunting desain template |

## Cara mengisi antrean

```
antrean/premium/5001/     <- nama folder = kode akun yang tercetak di kartu
  karakter/               3 screenshot lobi, skin berbeda -> jadi poster di TEMPLATE 1
  slide/                  screenshot mentah -> jadi kartu TEMPLATE 2, tiap 2 berkas 1 kartu
  fashion.png             1 screenshot layar Fashion -> ikonnya dipotong OTOMATIS
  item/                   biarkan kosong; diisi sendiri dari fashion.png
  info.txt                harga: 750.000
                          item: 3 4 6 7      (opsional, lihat di bawah)
  poster.png              opsional; kalau ada, dipakai menggantikan karakter/
```

**Folder tingkat memakai nilai database, bukan labelnya:**

| Folder | Tercetak di kartu |
|---|---|
| `antrean/premium/` | Sultan |
| `antrean/reguler/` | Reguler |
| `antrean/pelajar/` | Pelajar |

Folder bernama `sultan` akan menghentikan proses dengan pesan yang menjelaskan itu.

### Ikon item dipotong sendiri

Taruh **satu** screenshot layar Fashion di akar folder akun — namanya bebas.
`item/` biarkan kosong; ia diisi otomatis tiap kali kamu menjalankan.

Tanpa keterangan tambahan, yang diambil **empat petak pertama**. Mau memilih
sendiri, tambahkan satu baris di `info.txt`:

```
harga: 750.000
item: 3 4 6 7
```

Angkanya nomor petak dari atas, **berurutan sesuai slot kartu** — jadi `3` muncul
di kotak paling kiri.

Mengubah barisnya saja tidak cukup kalau kartunya sudah pernah jadi: akun itu akan
dilewati. Hapus foldernya di `siap-upload` dulu, baru jalankan lagi. `item/` sendiri
tidak perlu dikosongkan — ia diisi ulang tiap kali akunnya dirakit.

Mau lihat semua petaknya dulu sebelum memilih?

```bash
python3 mesin/potong_item.py "antrean/premium/5001/fashion.png" /tmp/lihat
open /tmp/lihat
```

**Jangan taruh dua gambar di akar folder akun** — mesin tidak bisa menebak mana
screenshot Fashion-nya, jadi foldernya dilewati.

### Kenapa namanya `slide`

Karena isinya jadi **Template 2** — kartu bergambar dua layar bertumpuk. Tiap dua
berkas di `slide/` jadi satu kartu, jadi jumlahnya harus genap. Empat berkas jadi
dua kartu, enam jadi tiga.

Isinya screenshot mentah dari game: layar Vault, Collection, Fashion, apa pun yang
memperlihatkan skin yang kamu jual. Ini yang jadi bukti buat pembeli.

## Mengganti latar poster

```
latar/pelajar.png
latar/reguler.png
latar/premium.png    <- yang tampil "Sultan"
```

Nama berkas mengikuti **nilai database**, jadi `premium.png` bukan `sultan.png`.
Ukurannya **2353 × 2521**; kalau beda, mesin akan memotongnya di tengah dan bagian
tempat karakter berdiri bisa hilang.

Mau ganti suasana? Timpa saja berkasnya. Mesin tidak perlu diubah.

## Dua cara memberi poster

**Cara 1 — biar mesin yang merakit.** Isi `karakter/` dengan 3 screenshot lobi, jangan
taruh `poster.png`. Mesin memotong karakternya dan menyusun poster di atas latar sesuai
tingkat. Skin senjata dijamin asli karena itu piksel screenshot-mu sendiri.

### Menentukan siapa di tengah

**Urutan nama berkas menentukan posisinya.** Berkas pertama jadi kiri, kedua tengah,
ketiga kanan. Yang tengah digambar lebih besar, jadi taruh karakter andalanmu di situ.

Cara paling jelas: namai `1`, `2`, `3`.

```
karakter/1.jpeg    <- kiri
karakter/2.jpeg    <- TENGAH, paling besar
karakter/3.jpeg    <- kanan
```

Mau menukar? Tukar angkanya, lalu jalankan lagi. Ekstensinya bebas — yang dibaca cuma
urutan namanya. Nama bawaan dari WhatsApp juga jalan, tapi urutannya mengikuti jam
pengambilan, bukan pilihanmu.

Karakternya dinaikkan resolusinya empat kali lipat sebelum ditempel — kecuali
potongannya sudah cukup besar untuk ukuran tayang — jadi screenshot lobi yang
tampak buram di HP tetap terbaca tajam di kartu. Yang dinaikkan cuma
ketajamannya — senjata, skin, dan pose tetap yang kamu potret.

**Cara 2 — pakai poster Gemini.** Taruh `poster.png` di folder akun. Mesin memakainya apa
adanya dan mengabaikan `karakter/`.

Boleh dicampur: sebagian akun cara 1, sebagian cara 2.

**Di Windows cuma cara 2 yang jalan.** Pemotong karakternya memakai Vision, bawaan
macOS, dan tidak ada padanannya di sana. Akun tanpa `poster.png` akan menghentikan
proses dengan pesan yang menjelaskan itu — bukan diam-diam menghasilkan kartu tanpa
poster. Sisanya berjalan penuh: kartu slide, ikon item yang dipotong otomatis, semua
sama persis.

## Kalau pakai cara 1 — satu aturan penting

Pemotong memotong **gumpalan yang menyatu**, bukan "karakter". Pet atau sayap yang
**menempel** ke tubuh atau senjata ikut terbawa; yang berdiri **terpisah** hilang tanpa
suara. Rapatkan dulu sebelum screenshot kalau mau ikut tampil.

Yang sudah terbawa **tidak bisa dibuang lagi**. Pet yang menempel di bilah pedang menyatu
dengan pedangnya — membuangnya berarti memotong senjata, dan skin senjata itu barang yang
dibayar pembeli. Yang mesin lakukan: pet tidak dihitung sebagai badan, jadi orangnya yang
dipusatkan, dan pet-nya jatuh di **belakang** karakter sebelahnya. Ia mengintip, tidak
menutupi. Kalau kamu tidak mau pet-nya tampil sama sekali, lepas dulu di game sebelum
screenshot.

## Kalau pakai cara 2 — satu aturan penting

Minta Gemini membuat posternya sekitar **2353 × 2521**. Keluaran mentah yang tegak
(mis. 604×1024) tetap jadi, tapi 37% tingginya terbuang dan kepala atau kaki karakter
bisa terpotong. Mesin akan memberi peringatan kalau itu terjadi.

## Membaca hasilnya

Setelah jalan, mesin mencetak empat hal terpisah:

- **berkas dibuat** — ada di `siap-upload/`, siap diunggah
- **akun sudah ada** — kartunya sudah ada dari lari sebelumnya, tidak dibuat ulang
- **PERINGATAN** — kartunya jadi, tapi lihat dulu sebelum dipakai
- **folder DILEWATI** — tidak jadi, beserta alasan yang bisa langsung kamu perbaiki

Peringatan lain yang mungkin muncul: `karakter diperkecil N%`. Artinya salah satu
karakter berpose melebar — kaki mengangkang atau tangan terentang — sehingga ketiganya
tidak muat berdampingan dengan celah. Mesin mengecilkan ketiganya seperlunya supaya
tetap ada jarak yang terlihat di antara mereka. Kalau angkanya besar dan kartunya jadi
terasa kecil, ganti screenshot karakter itu dengan pose yang lebih rapat.

Yang diukur **badannya saja**. Jubah yang mengembang, aura, dan senjata yang menjulur
mendatar tidak ikut dihitung — ketiganya boleh menyelinap di belakang tetangganya, bahkan
sedikit keluar tepi jendela. Ini disengaja: satu jubah lebar dulu mengerdilkan ketiga
karakter sekaligus, dan jubah terpotong sedikit jauh lebih murah daripada itu.

Salah satu peringatan yang mungkin muncul: `karakter/` berisi berkas yang isinya
identik. Artinya kamu menaruh satu screenshot yang sama beberapa kali — sering
terjadi kalau berkasnya digandakan jadi `copy` dan `copy 2`. Posternya tetap
dibuat, tapi akan memajang karakter yang sama lebih dari sekali. Peringatan ini
cuma berlaku untuk akun yang tidak punya `poster.png` sendiri — begitu ada
poster.png, `karakter/` tidak pernah dibaca, jadi tidak ada yang diperiksa kembar.

Akun yang dirakit selalu keluar bersih: sisa lari sebelumnya dibuang dulu, jadi kartu
slide yang jumlahnya berkurang tidak meninggalkan berkas nyasar. Yang **tidak** dirakit
tentu saja tetap seperti apa adanya — itu gunanya daftar "akun sudah ada".

Kalau ada yang salah pasang — nama tingkat keliru, aset hilang, kode akun kembar — mesin
**berhenti total** dengan pesan `BERHENTI:`, bukan diam-diam menghasilkan 30 kartu salah.

## Cara mengunggah

Tiap akun punya foldernya sendiri, dinamai kodenya:

```
siap-upload/FF-PELAJAR-6001/
  FF-PELAJAR-6001-utama.webp
  FF-PELAJAR-6001-slide-1.webp
  FF-PELAJAR-6001-slide-2.webp
```

Buka satu folder, unggah isinya, tutup. Tidak perlu memungut berkas satu akun di
antara berkas akun lain. Kodenya tetap menempel di tiap nama berkas, jadi yang
terlanjur terseret keluar folder masih bisa dikenali.

- **Foto #1** — `<kode>-utama.webp`. Ini yang jadi thumbnail dan gambar preview
- **Foto #2 dst** — kartu slide, lalu screenshot mentah dari `slide/`

Kartu utama itu materi promosi; screenshot mentah buktinya. Pembeli yang tertarik dari
daftar membuka halaman dan menemukan skin yang sebenarnya.

## Lari pertama mengunduh sekali

Kali pertama kamu merakit poster dari `karakter/`, mesin mengambil biner
penaik-resolusi (± 52 MB) dari rilis resmi Real-ESRGAN. Ia mencetak barisnya,
jadi layar tidak akan diam tanpa penjelasan. Setelah itu ia tersimpan di
`mesin/upscaler/` dan tidak pernah diunduh lagi.

Arsipnya diperiksa sidik jarinya sebelum dipakai. Kalau tidak cocok, atau
kalau jaringan mati saat unduhan dibutuhkan, akun itu masuk daftar folder
DILEWATI dengan alasannya tercetak jelas — bukan diam-diam menghasilkan kartu
yang kamu kira sudah HD. Akun lain di antrean tetap lanjut dirakit.

Butuh jaringan hanya pada lari pertama itu.

## Kalau pemeriksanya merah

`python3 mesin/uji_rakit.py` harus melaporkan semua lulus. Kalau ada yang
merah soal "biner pemotong belum dikompilasi", jalankan sekali:

```bash
swiftc -O -o mesin/potong mesin/potong.swift
```

Biner itu sengaja tidak masuk git, jadi perlu dikompilasi ulang di tiap salinan repo.

Di Windows dua cek berlabel `potong ...` tampil sebagai **lewat**, bukan merah, dan
totalnya menyesuaikan sendiri. Itu benar: keduanya menjalankan biner Vision yang
memang tidak bisa ada di sana. Yang merah tetap berarti ada yang rusak.

## Catatan

Perkakas ini repo mandiri, lepas dari repo jagotopup. Cabang utamanya `main`, dan
seluruh isinya ada di akar repo ini — tidak perlu berpindah cabang untuk menggarapnya.
