# Perlakuan karakter pada poster — rancangan

> **CATATAN SEJARAH — jangan dipakai sebagai rujukan nilai.**
>
> Dokumen ini rancangan tertanggal 8 Agustus dan sudah dilampaui pekerjaan
> 9 dan 14 Agustus. Alasan-alasannya masih berlaku dan itulah nilainya;
> ANGKA-ANGKANYA tidak. Yang berubah sesudahnya:
>
> | Hal | Di sini | Sekarang |
> |---|---|---|
> | Ekspor | 1080 × 1350 | 2608 × 3260, mutu 100 |
> | `TINGGI_KARAKTER` | 0,60 | 0,72 |
> | `GARIS_DASAR` | 0,86 | 0,95 |
> | `POS_X` | 0,23 / 0,50 / 0,77 | dihapus — celah dibagikan di `tata_letak` |
> | Lebar yang menentukan tata letak | kotak-batas alfa | inti badan (`inti_alfa`, `INTI_CAKUPAN` 0,30) |
> | Urutan tempel | kiri, kanan, tengah terakhir | tengah dulu, sisi di atasnya |
> | Letak keluaran | berkas datar di akar `siap-upload/` | satu folder per akun |
> | Cakupan tiap lari | selalu merakit seluruh antrean | yang kartunya sudah ada dilewati; `--ulang` memaksa |
>
> Ditambahkan sesudah rancangan ini ditulis: bloom senjata, rim light, jaminan
> celah antar karakter, peringatan kontras label, penjaga ruang kepala, dan
> penjaga batas unggah situs.
>
> Empat baris terakhir tabel itu lahir 14 Agustus dari satu keluhan: karakter
> terbaca kerdil. Akarnya, lebar diukur dari kotak-batas alfa, sehingga jubah
> dan peliharaan yang menempel dihitung seberat badan dan menyusutkan ketiganya.
> Alasan tiap angkanya, berikut pengukuran yang memunculkannya, ada di komentar
> `INTI_CAKUPAN` dan `inti_alfa` di `mesin/poster.py`.
>
> **Sumber kebenaran ada di komentar `mesin/poster.py` dan `mesin/template.py`**,
> yang menyimpan alasan tiap angka berikut pengukurannya. Dokumen ini disimpan
> karena ia merekam bagaimana keputusan awal diambil — termasuk yang kemudian
> terbukti keliru dan dibalik.

Tanggal: 8 Agustus 2026
Berkas yang disentuh: `mesin/poster.py`, `mesin/antrean.py`, `mesin/uji_rakit.py`,
`.gitignore`, `BACA-DULU.md`

Ongkos waktu, diukur pada M4 dengan kutout 226 × 570: **1,3 detik per karakter**
saat panas dengan model `realesrgan-x4plus-anime`, jadi sekitar 4 detik per akun
dan ± 2 menit untuk tiga puluh akun. Lari pertama menambah sekali ± 1,3 detik
untuk kompilasi shader Vulkan, yang sesudahnya di-cache.

Dua angka yang sempat tertulis di rancangan ini dan sudah dikoreksi: 1,7 detik
(itu lari pertama yang memuat ongkos kompilasi sekali-seumur-hidup, bukan biaya
per karakter), lalu 0,37 detik (itu benar, tapi untuk `realesr-animevideov3`
yang kemudian diganti — lihat "Pilihan model, dan pembalikannya").

## Masalah

Pemilik melihat `666-utama.webp` dan menilai ketiga karakternya "tidak HD sama
sekali, malah burik". Yang diinginkan: karakter setajam dan sepunya-gigit hasil
edit Free Fire yang beredar di TikTok.

## Bukti terukur

Diukur pada bahan nyata `antrean/pelajar/666/` tanggal 8 Agustus 2026:

| Yang diukur | Nilai |
|---|---|
| Screenshot sumber | 1600 × 739, JPEG, 178 KB |
| Kepadatan sumber | 1,23 bit/piksel; kuantisasi DC = 5 |
| Kutout karakter setelah Vision | 226 × 570 piksel |
| Digambar di poster | 1513 px (samping), 1724 px (tengah) |
| Poster ke kartu | × 0,413 |
| Tinggi akhir di kartu | 625 px (samping), 713 px (tengah) |
| Pembesaran bersih dari sumber | 1,10× dan 1,25× |

## Akar masalah

Tiga sebab bertumpuk. Hipotesis pertama — WhatsApp merusak berkas — **ditolak
oleh bukti**: 1,23 bit/piksel dengan kuantisasi DC 5 adalah JPEG sehat.

1. **Karakternya memang hanya punya 226 × 570 piksel asli.** Free Fire me-render
   di resolusi rendah demi menjaga FPS di perangkat kelas menengah, jadi
   screenshot-nya lahir sudah kurang detail. Pembesaran oleh mesin cuma
   1,1–1,25×, jadi mesin bukan perusaknya — bahannya yang tipis sejak awal.

2. **Latarnya foto beresolusi penuh yang tajam.** Alur ban, serat kayu, dan helai
   rumput terbaca jelas. Mata menilai ketajaman secara relatif: karakter lembek
   yang berdiri di atas latar setajam silet akan selalu terbaca burik, berapa pun
   angka pembesarannya.

3. **Karakter gelap dan berkontras rendah** dibanding latar siang yang cerah,
   dan tepi rambutnya berjumbai sisa segmentasi.

Sebab nomor 2 yang paling menentukan. Memblur latar memberi perbaikan lebih
besar daripada mempertajam karakter, karena ia menghentikan perbandingan yang
merugikan itu.

### Sebab tambahan di luar kendali mesin

Semua berkas sumber bernama `WhatsApp Image ...` dan sisi panjangnya tepat 1600 —
batas kompresi WhatsApp untuk kiriman jenis *Foto*. Rasio 1600 × 739 = 2,165
cocok dengan layar 2340 × 1080 (2,167), jadi screenshot aslinya kemungkinan besar
2340 × 1080 dan sudah dipangkas 1,46× sebelum menyentuh mesin. Kirim lewat
AirDrop atau sebagai *Dokumen* akan menaikkan kutout ke sekitar 330 × 833.

Pemilik memilih tidak menempuh jalur itu sekarang — sengaja, supaya bahan yang
sudah ada dimaksimalkan dulu. Perlakuan yang dirancang di sini tidak bergantung
resolusi sumber, jadi hasilnya menumpuk, bukan mubazir, ketika sumbernya naik.

## Yang dibangun

Tiga sentuhan di dalam `poster.rakit()`, dengan urutan yang mengikat.

### 0. Kutout dinaikkan resolusinya

Setiap kutout dinaikkan 4× oleh Real-ESRGAN model `realesrgan-x4plus-anime` sebelum
diskalakan ke ukuran tayang. Disisipkan **sesudah** `_kikis_pinggiran`, karena
`KIKIS_PIKSEL = 2` dikalibrasi pada skala sumber dan akan salah takaran kalau
dijalankan pada gambar yang sudah membesar empat kali.

Alasannya dua, dan yang kedua tidak kentara:

**Ia membalik arah rantai skala.** Sekarang kutout 226 × 570 *dibesarkan* 2,65×
menjadi 1513 px. Setelah 4×, kutout 904 × 2280 justru *dikecilkan* menjadi
1513 px (0,66×) dan 1724 px (0,76×). Mengecilkan selalu lebih bersih daripada
membesarkan. Skala 2× tidak cukup — ia masih menyisakan pembesaran 1,33×.

**Ia membuang derau yang selama ini membatasi ketajaman.** Diuji berdampingan:
tanpa upscale, structure dan sharpen dengan angka di bawah membuat sweter hitam
berbintik, karena keduanya memperkuat derau JPEG yang ada. Dengan upscale, angka
yang sama persis menghasilkan kain bersih. Kedua lapis ini saling melengkapi,
bukan mengulang.

Hasilnya paling terasa pada barang dagangan itu sendiri: tulisan "FIRE" di badan
senjata yang tadinya bubur tak terbaca menjadi terbaca jelas, dengan bentuk
huruf, emblem, dan pola api yang sama seperti aslinya.

#### Upscale hanya kalau ia menolong

Upscale dilewati kalau tinggi kotak alfa kutout **sudah ≥ tinggi tayangnya**
(1724 px, ukuran karakter tengah). Pada keadaan itu rantainya sudah mengecil
tanpa bantuan, dan menaikkannya 4× hanya untuk menurunkannya lagi adalah
pemborosan murni.

Bukan skenario khayalan — ia terjadi persis ketika pemilik pindah ke AirDrop,
momen yang justru dirancang untuk dinikmati. Diukur:

| Kutout masuk | Waktu | Keluar |
|---|---|---|
| 226 × 570 | 0,37 s | 904 × 2280 |
| 330 × 833 | 0,64 s | 1320 × 3332 |
| 900 × 2270 | 4,28 s | 3600 × 9080 |

Baris terakhir menghabiskan 4,28 detik dan ± 131 MB memori untuk melahirkan
32,7 megapiksel yang seluruhnya dibuang saat dikecilkan ke 1513 px. Penjaga ini
mencegahnya, dan ongkosnya satu perbandingan bilangan.

#### Catatan: kenapa ini tidak melanggar prinsip "tidak pernah digambar ulang"

Keberatan sempat diajukan bahwa upscaler AI mengarang piksel, sehingga
bertabrakan dengan pernyataan di kepala `poster.py`: karakter tidak pernah
digambar ulang karena skin senjata adalah barang yang dibayar pembeli.

Keberatan itu salah tempat, dan pemilik benar menolaknya. `BACA-DULU.md`
menyatakan pembagian kerjanya sendiri: **"Kartu utama itu materi promosi;
screenshot mentah buktinya."** Bukti dagang hidup di `slide/` — screenshot
mentah, tidak tersentuh perlakuan apa pun. Poster memang materi promosi.

Ditambah, yang diperiksa berdampingan menunjukkan upscaler merekonstruksi,
bukan mengganti: huruf yang sama, emblem yang sama, pola api yang sama, hanya
bersih. Ia tidak mengubah skin mana yang dipegang. Prinsip itu tetap berlaku
penuh di tempat ia memang berlaku, yaitu `slide/`.

### 1. Latar dikalahkan

Latar dibuka, diblur, lalu diredupkan. Sesudah itu barulah bayangan kaki
ditempel dan karakter dipasang. Bayangan harus digambar **setelah** blur; kalau
sebelum, ia ikut terblur dua kali dan kaki kehilangan pijakan visual.

### 2. Karakter dimenangkan

Tiap kutout diperlakukan **setelah** diskalakan ke ukuran akhir, bukan sebelum.
Mempertajam sebelum resize sia-sia karena resampling membubarkan hasilnya.

Urutan operasi dalam satu kutout:

1. **Structure** — `UnsharpMask(radius=28, percent=60, threshold=0)`
2. **Sharpen** — `UnsharpMask(radius=2.5, percent=130, threshold=3)`
3. **Kontras** — × 1,14
4. **Saturasi** — × 1,20

Structure dan sharpen adalah operasi berbeda, bukan pengulangan. Radius besar
dengan kadar sedang mengangkat kontras lokal frekuensi menengah — tekstur kain,
lipatan, ukiran senjata — tanpa menyentuh tepi siluet, sehingga tidak melahirkan
halo. Radius kecil dengan kadar tinggi menegaskan tepi. Editor Free Fire di
TikTok memakai keduanya (Snapseed: Structure dan Sharpen didorong bersamaan);
rancangan awal hanya punya sharpen dan terbukti kurang berisi saat dibandingkan
berdampingan.

Ambang 3 pada langkah sharpen bukan hiasan. Ia menahan bidang gelap yang rata
agar tidak ikut dipertajam. Varian uji dengan ambang 2 dan kadar 185 membuat
sweter hitam berbintik derau — cacat yang sama yang diperingatkan dokumentasi
Snapseed soal structure dan sharpen berlebih.

### Kanal alfa dijaga terpisah

Semua operasi di atas hanya menyentuh RGB. Kanal alfa disalin utuh dari masukan.
Kalau alfa ikut dipertajam, tepinya melahirkan halo — persis cacat yang
`KIKIS_PIKSEL` sudah susah payah buang.

### Konstanta

Ditulis sebagai konstanta modul mengikuti gaya `TINGGI_KARAKTER` dan
`GARIS_DASAR` yang sudah ada: bernilai tetap antar akun, beralasan tertulis,
bukan berkas konfigurasi untuk nilai yang tidak pernah disetel ulang.

```
UPSCALE_MODEL = 'realesrgan-x4plus-anime'
UPSCALE_SKALA = 4
LATAR_BLUR    = 7          # piksel, pada kanvas 2353 × 2521
LATAR_REDUP   = 0.88
STRUKTUR      = (28, 60)   # radius, persen; ambang selalu 0
UNSHARP       = (2.5, 130, 3)
KONTRAS       = 1.14
SATURASI      = 1.20
```

Ambang pelewatan upscale tidak jadi konstanta tersendiri: ia diturunkan dari
`TINGGI_KARAKTER × SKALA_TENGAH × tinggi kanvas` yang sudah ada. Menuliskannya
sebagai angka kedua berarti dua sumber kebenaran yang bisa berselisih diam-diam
kalau tata letaknya disetel ulang.

### Pemecahan fungsi

`poster.rakit()` sudah memikul buka latar, potong, tata letak, bayangan, tempel,
dan rona. Menumpuk tujuh operasi baru di dalamnya membuatnya jadi fungsi yang
tidak bisa dipahami sekali baca, dan uji 1–3 memang mengandaikan bagian-bagiannya
bisa dipanggil sendiri. Maka tiga penolong baru, masing-masing satu tugas:

| Fungsi | Tugas | Bergantung pada |
|---|---|---|
| `_naikkan_resolusi(im)` | Kutout RGBA masuk, RGBA 4× keluar; melewat kalau sudah cukup besar | biner + model |
| `_perlakukan_latar(im)` | Blur lalu redupkan | `LATAR_BLUR`, `LATAR_REDUP` |
| `_perlakukan_karakter(im)` | Structure, sharpen, kontras, saturasi; alfa disalin utuh | empat konstanta rasa |

`rakit()` tinggal memanggil ketiganya pada urutan yang sudah ditetapkan.

Angka-angka ini dipilih dengan merender varian nyata dari bahan 666 dan
membandingkannya berdampingan, bukan dikira-kira.

### Pilihan model, dan pembalikannya

Semula `realesr-animevideov3` yang dipilih, dengan alasan ia paling menjaga
tekstur kain sementara `realesrgan-x4plus-anime` dan `realesrgan-x4plus`
dianggap terlalu melukis.

Keputusan itu **dibalik 9 Agustus**, dan catatan ini sengaja menyimpan
keduanya. Dua sebab:

Pertama, ukurannya salah. Sebagian "tekstur" yang dijaga `animevideov3` adalah
derau JPEG dari sumber WhatsApp, bukan detail. Yang diinginkan pemilik adalah
rupa yang halus dan melukis — yang terbaca **mewah**, bukan yang terbaca
berbutir. Ia menyebutnya sendiri: "biar megah dan terlihat mewah dan mahal".

Kedua, perbandingan pertama dibuat pada ekspor 1080 × 1350, waktu ketiga model
sama-sama tergencet sehingga bedanya tidak terlihat. Diadu ulang pada ekspor
2160 × 2700, `x4plus-anime` menang telak di wajah dan kain — dan **tidak kalah
di ukiran senjata**, alasan asli memilih `animevideov3`. Apinya justru lebih
bersih dan motif bandana di celana lebih tegas.

Ongkosnya 1,3 detik per karakter, dari 0,37.

## Mengambil biner upscaler

Biner `realesrgan-ncnn-vulkan` dan model `realesrgan-x4plus-anime` tidak masuk
git, sebagaimana biner `potong`. Bedanya, ia tidak bisa dikompilasi sendiri, jadi
mesin **mengunduhnya sendiri** saat pertama kali dibutuhkan.

Yang dipakai hanya biner (26 MB) dan satu model (1,2 MB); sembilan model lain di
dalam arsip tidak diekstrak.

Karena mesin akan menjalankan kode yang baru saja diunduh, arsipnya diverifikasi
lebih dulu terhadap sidik jari yang dipatok:

```
sumber : https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/
         realesrgan-ncnn-vulkan-20220424-macos.zip
ukuran : 51 817 124 bita
sha256 : e0ad05580abfeb25f8d8fb55aaf7bedf552c375b5b4d9bd3c8d59764d2cc333a
```

Kalau sidik jarinya tidak cocok — rilis diganti, unduhan rusak, atau ada yang
menyusup di tengah jalan — mesin **BERHENTI** dan tidak menjalankan apa pun.
Berkas yang tidak dikenal tidak pernah dieksekusi. Kalau jaringan mati saat
unduhan dibutuhkan, mesin juga berhenti dengan pesan yang menyebutkan itu,
bukan diam-diam mundur ke jalur lama.

Setelah diekstrak, atribut karantina macOS dilepas dari biner dan model, dan
biner diberi izin eksekusi.

Unduhan 52 MB tidak boleh berlangsung tanpa suara. `jalankan.command` diklik dua
kali dan layar diam adalah tanda macet, bukan tanda bekerja. Maka sebelum
unduhan dimulai mesin mencetak satu baris yang menyebut apa yang diambil dan
berapa besarnya, dan satu baris lagi ketika selesai. Ini hanya terjadi sekali
seumur salinan repo.

## Karakter kembar diperingatkan

Ketiga berkas di `antrean/pelajar/666/karakter/` ternyata **md5 identik** — satu
screenshot yang digandakan dan diberi akhiran `copy` dan `copy 2`. Poster yang
dihasilkan memajang karakter yang sama tiga kali: pose sama, skin sama, senjata
sama. Diperiksa: mesin tidak punya deteksi kembar sama sekali.

Ini bukan cacat yang diperbaiki perlakuan gambar, tetapi ia merusak penilaian
atas perlakuan itu. Tanpa peringatan, pemilik menjalankan ulang setelah semua
pekerjaan ini selesai, tetap melihat tiga kloning, dan wajar menyimpulkan
kerjanya gagal — padahal yang salah isi antreannya.

Maka `antrean.py` membandingkan isi ketiga berkas `karakter/` dan mencatat
**PERINGATAN** kalau ada yang identik, memakai jalur peringatan yang sudah ada.
Bukan `DILEWATI` dan bukan `BERHENTI`: kartunya tetap dibuat, karena pemilik yang
berhak memutuskan apakah tiga karakter kembar itu memang disengaja.

## Yang sengaja TIDAK dibangun

**Jalur `poster.png` buatan Gemini.** Poster Gemini adalah satu gambar utuh;
latar dan karakternya menyatu, jadi mesin tidak bisa memisahkan mana yang harus
tajam dan mana yang harus mundur. Ini tidak butuh percabangan baru: `rakit()`
memang hanya dipanggil ketika akun tidak punya `poster.png`, jadi jalur Gemini
tak tersentuh dengan sendirinya.

**Render langsung di resolusi ekspor.** Setelah upscaler dipasang, kutout 2280 px
dikecilkan ke 1513 px di poster, lalu seluruh kartu dikecilkan lagi 0,413× ke
625 px. Dua kali resampling, tetapi kini keduanya mengecilkan — jauh lebih jinak
daripada keadaan sebelumnya yang membesarkan lalu mengecilkan. Merender sekali
langsung dari 2280 px ke ukuran akhir tetap sedikit lebih tajam, tetapi itu
membongkar `template.py` dan berada di luar lingkup yang diminta. Dicatat sebagai
pekerjaan lain, dan nilainya sekarang lebih kecil daripada sebelum upscaler ada.

## Uji

Ditulis lebih dulu, sebelum kode jalannya ada.

Uji 1 sampai 3 menguji fungsi perlakuannya langsung, bukan poster jadi. Poster
jadi memuat karakter yang dipertajam DI ATAS latar yang diblur, jadi mengukur
seluruh kanvas mencampur dua efek yang berlawanan arah dan tidak membuktikan
apa pun.

1. **Alfa utuh.** Alfa keluaran fungsi perlakuan karakter identik
   piksel-per-piksel dengan alfa masukan — membuktikan perlakuan tidak
   melahirkan halo tepi.
2. **Latar benar-benar mundur.** Fungsi perlakuan latar diberi gambar uji
   beralur tajam; energi tepi keluarannya — rerata magnitudo `FIND_EDGES` —
   harus turun dibanding masukan, dan kecerahan reratanya harus turun mendekati
   faktor `LATAR_REDUP`.
3. **Karakter benar-benar maju.** Fungsi perlakuan karakter diberi kutout uji;
   energi tepi keluarannya harus NAIK dibanding masukan, diukur dengan metrik
   yang sama seperti uji 2 supaya kedua arah dibandingkan setara.
4. **Tata letak tidak bergeser.** Keluaran `tata_letak` untuk kotak alfa yang
   sama identik dengan dan tanpa perlakuan — perlakuan mengubah piksel, bukan
   geometri.
5. **Jalur Gemini bersih.** Akun berposter `poster.png` tidak pernah menyentuh
   ketiga fungsi penolong itu sama sekali — dibuktikan dengan menggantinya
   sementara oleh versi yang meledak kalau dipanggil. Versi lama uji ini menuntut
   kartu identik piksel-per-piksel dengan sebelum perubahan; itu menuntut berkas
   emas yang harus disimpan dan dirawat, dan akan merah karena alasan yang tidak
   ada hubungannya begitu templatenya disentuh.
6. **Karakter kembar diperingatkan.** Folder `karakter/` berisi tiga berkas
   dengan isi identik menghasilkan satu PERINGATAN, dan kartunya tetap dibuat.

Uji khusus upscaler. Kelompok ini dilewati otomatis kalau binernya belum ada,
supaya `uji_rakit.py` tetap hijau di mesin yang belum lengkap tanpa merah palsu:

7. **Keluar 4× dengan alfa utuh.** Kutout 226 × 570 RGBA keluar 904 × 2280 RGBA,
   dan porsi piksel alfa separuh-tembus tidak melonjak — terukur 13,90% menjadi
   13,96%, rasio 1,00×. Ini membuktikan kanal alfa ikut diskalakan dengan benar,
   bukan dibuang lalu diisi tepi kabur yang akan lahir jadi halo.
8. **Keluarannya deterministik.** Dua lari atas masukan yang sama menghasilkan
   berkas dengan sha256 identik. Sudah terbukti pada biner ini, jadi uji lain
   boleh menuntut kesamaan piksel persis tanpa takut rapuh.
9. **Rantai skala berbalik arah.** Untuk kotak alfa hasil upscale, faktor yang
   dihitung `tata_letak` harus lebih kecil dari 1,0 — mengecilkan, bukan
   membesarkan. Ini menjaga alasan utama memilih 4×: kalau suatu saat skalanya
   diturunkan ke 2×, uji ini merah.
10. **Kutout yang sudah besar dilewati.** Kutout yang tinggi alfanya melebihi
    tinggi tayang keluar tanpa berubah sama sekali, dan binernya tidak dipanggil.

Uji alur pengambilan biner. Ini bagian paling berisiko dari seluruh rancangan —
mesin mengeksekusi kode yang baru diunduh — sekaligus yang paling mudah lolos
tanpa diuji, jadi ketiganya wajib:

11. **Sidik jari salah ditolak.** Arsip yang sha256-nya tidak cocok menghentikan
    proses, dan tidak satu bita pun darinya pernah dieksekusi atau diekstrak.
12. **Jaringan mati berhenti dengan jujur.** Kalau unduhan dibutuhkan tapi gagal,
    mesin BERHENTI menyebut sebabnya — tidak mundur diam-diam ke LANCZOS dan
    tidak menghasilkan kartu yang dikira sudah HD.
13. **Ekstraksi selektif.** Hanya biner dan `realesrgan-x4plus-anime` yang keluar
    dari arsip; sembilan model lain tidak ikut ditulis ke disk.

## Sumber riset

- [Screenshot Free Fire Buram — VCGamers](https://www.vcgamers.com/news/cara-jadikan-hd-screenshot-free-fire-buram-dalam-hitungan-detik/)
- [Cara Setting Grafik Free Fire HD — GGWP.ID](https://www.ggwp.id/esports/battle-royale/cara-setting-grafik-free-fire-hd-00-s0rct-2tx29n)
- [Perbedaan Free Fire dan Free Fire MAX — Dafunda](https://dafunda.com/game/perbedaan-free-fire-dan-free-fire-max/)
- [Foto FF jadi HD dengan Wink dan Efiko — Lemon8](https://www.lemon8-app.com/@zart_sdu/7661166612351943189?region=id)
- [Details: Structure & Sharpening — Snapseed Help](https://support.google.com/snapseed/answer/3113306?hl=en)
