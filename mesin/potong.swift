// Pemotong subjek berbasis Vision — bawaan macOS 14+, model yang sama dengan
// "Remove Background" di Preview. Tanpa pemasangan, tanpa unduhan model,
// tanpa jaringan.
//
// Kompilasi: swiftc -O -o potong potong.swift
// Pakai:     ./potong masuk.png keluar.png
//
// Keluar dengan kode bukan-nol kalau tidak ada subjek. TIDAK PERNAH
// mengembalikan gambar utuh berlatar sebagai cadangan: karakter yang masih
// membawa potongan lobi game, tertempel di atas latar lain, adalah cacat yang
// lolos tanpa terlihat.
//
// Terukur 8 Agu 2026 dengan tiga screenshot lobi utuh milik pemilik
// (2868x1320, seluruh UI game kelihatan): ketiganya terpotong bersih —
// tombol, banner, dan daftar teman di lobi semua diabaikan, senjata utuh
// ikut terbawa (itu bagian dari barang dagangan).
//
// Aturan yang menentukan apa yang lolos: Vision memotong MASSA LATAR-DEPAN
// YANG TERSAMBUNG, bukan "si karakter". Bukti dari dua screenshot yang
// sama-sama punya peliharaan di samping pemain: di satu berkas peliharaan
// menyentuh laras senjata dan ikut terbawa; di berkas lain peliharaan berdiri
// sedikit terpisah dan dibuang. Aturan yang sama menjelaskan kasus sayap
// mekanik sebuah karakter yang hilang — sayap itu dirender terpisah dan
// separuh tembus pandang. Kalau ada aksesori yang mau dipastikan ikut
// terpotong, pastikan pikselnya menyentuh tubuh karakter di screenshot
// sumbernya; yang terpisah akan dibuang.
//
// Cakupan subjek pada kotak pembatas yang dikembalikan: 42-47% di ketiga
// contoh di atas — jangan kaget kalau sebagian besar kotak ternyata latar.

import CoreImage
import Foundation
import Vision

func mati(_ pesan: String, _ kode: Int32) -> Never {
    FileHandle.standardError.write(("potong: " + pesan + "\n").data(using: .utf8)!)
    exit(kode)
}

let arg = CommandLine.arguments
guard arg.count == 3 else { mati("pakai: potong <masuk> <keluar>", 2) }

let masuk = URL(fileURLWithPath: arg[1])
let keluar = URL(fileURLWithPath: arg[2])

guard let citra = CIImage(contentsOf: masuk) else {
    mati("tidak bisa membaca gambar: \(masuk.lastPathComponent)", 2)
}

let permintaan = VNGenerateForegroundInstanceMaskRequest()
let penangan = VNImageRequestHandler(ciImage: citra)

do {
    try penangan.perform([permintaan])
} catch {
    mati("Vision gagal pada \(masuk.lastPathComponent): \(error.localizedDescription)", 3)
}

guard let hasil = permintaan.results?.first, !hasil.allInstances.isEmpty else {
    mati("tidak ada subjek yang ditemukan di \(masuk.lastPathComponent)", 4)
}

// HANYA INSTANCE TERBESAR. Vision memisahkan pet, hewan peliharaan, dan sosok
// lain yang berdiri di dekat karakter sebagai instance tersendiri. Mengambil
// semuanya membawa pet ikut ke poster — diminta pemilik supaya tidak.
//
// Diukur 8 Agu 2026 pada tiga screenshot lobi pemilik: karakter selalu jauh lebih
// besar daripada pet (343x1035 lawan 258x486; 326x1045 lawan 270x404), jadi luas
// kotak-batas memisahkan keduanya dengan selisih lebar. Senjata TIDAK pernah jadi
// instance terpisah — ia menyentuh tangan, jadi menyatu dengan karakternya.
//
// TIDAK ADA CEK OTOMATIS UNTUK PEMILIHAN INI, dan itu disengaja. Dicoba dua kali
// (8 Agu 2026) dengan gambar sintetis berisi dua sosok terpisah: Vision
// mengembalikan SATU instance saja kedua kali — sosok gambar sederhana tidak
// dianggapnya subjek kedua. Cek sintetis apa pun akan hijau tanpa pernah menguji
// pemilihan ini. Buktinya cuma pengukuran di atas, pada screenshot sungguhan.
// Kalau nanti pemilihan instance diubah, ukur ulang dengan cara yang sama —
// jangan percaya suite ini menangkapnya.
var terbesar = hasil.allInstances.first!
var luasTerbesar = 0
for i in hasil.allInstances {
    guard let buf = try? hasil.generateMaskedImage(ofInstances: [i],
                                                   from: penangan,
                                                   croppedToInstancesExtent: true) else { continue }
    let e = CIImage(cvPixelBuffer: buf).extent
    let luas = Int(e.width * e.height)
    if luas > luasTerbesar { luasTerbesar = luas; terbesar = i }
}

do {
    let buffer = try hasil.generateMaskedImage(ofInstances: [terbesar],
                                               from: penangan,
                                               croppedToInstancesExtent: true)
    let terpotong = CIImage(cvPixelBuffer: buffer)
    guard let ruang = CGColorSpace(name: CGColorSpace.sRGB) else {
        mati("ruang warna sRGB tidak tersedia", 5)
    }
    try CIContext().writePNGRepresentation(of: terpotong, to: keluar,
                                           format: .RGBA8, colorSpace: ruang)
} catch {
    // Penulis PNG membuat lalu memotong berkas tujuan sebelum enkode selesai —
    // kalau gagal di tengah jalan (disk penuh, izin dicabut, encoder error),
    // sisa berkas nol-byte atau rusak bisa tertinggal di `keluar`. Berkas
    // setengah jadi lebih buruk daripada tidak ada sama sekali: Task 8 tidak
    // bisa membedakannya dari potongan yang benar-benar valid.
    try? FileManager.default.removeItem(at: keluar)
    mati("gagal menulis \(keluar.lastPathComponent): \(error.localizedDescription)", 5)
}
