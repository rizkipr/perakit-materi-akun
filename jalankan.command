#!/bin/bash
# Klik dua kali dari Finder untuk merakit seluruh antrean.
#
# Finder menjalankan berkas .command dari direktori rumah, bukan dari sini, jadi
# baris pertama pindah ke folder skrip ini dulu. Tanpa itu path antrean/ dan
# siap-upload/ menunjuk ke tempat yang salah dan mesin melapor antrean kosong.
cd "$(dirname "$0")" || exit 1

echo "Merakit materi listing akun…"
echo

python3 mesin/rakit.py antrean siap-upload
kode=$?

echo
if [ $kode -eq 0 ]; then
    echo "Selesai. Buka folder siap-upload/ untuk mengambil kartunya."
    open siap-upload
else
    echo "Ada yang perlu diperbaiki — baca pesan di atas."
fi

echo
echo "Tekan Enter untuk menutup jendela ini."
read -r
