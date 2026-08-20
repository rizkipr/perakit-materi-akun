@echo off
rem Klik dua kali dari Explorer untuk merakit seluruh antrean.
rem
rem Sepadan dengan jalankan.command di macOS. Tiga hal berbeda dan ketiganya
rem perlu: Explorer menjalankan berkas .bat dari folder berkasnya sendiri
rem tapi belum tentu dari drive yang sama, perintah Python-nya bernama
rem "python" bukan "python3", dan konsol Windows tidak selalu berkode UTF-8
rem sementara pesan mesin ini memakai tanda pisah panjang.
cd /d "%~dp0" || exit /b 1
chcp 65001 >nul

rem Tanpa ini, Windows yang belum punya Python membuka Microsoft Store dan
rem jendelanya menutup tanpa pesan — tak terbedakan dari perkakas yang rusak.
where python >nul 2>&1
if errorlevel 1 (
    echo Python belum terpasang. Pasang dari python.org, centang
    echo "Add python.exe to PATH" saat memasang, lalu jalankan berkas ini lagi.
    echo.
    pause
    exit /b 1
)

echo Merakit materi listing akun...
echo.

python mesin\rakit.py antrean siap-upload
set kode=%errorlevel%

echo.
if %kode% equ 0 (
    echo Selesai. Buka folder siap-upload\ untuk mengambil kartunya.
    explorer siap-upload
) else (
    echo Ada yang perlu diperbaiki - baca pesan di atas.
)

echo.
pause
