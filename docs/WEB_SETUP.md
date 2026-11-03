# TRIWISE LAB — Panduan Simulasi Web

Website ini adalah porting logika dari `simulation/main.py` (Python + Tkinter) ke HTML, CSS, dan JavaScript agar berjalan tanpa instalasi Python pada browser modern.

## Folder

```
TRIWISE/
├─ simulation/main.py          # simulasi desktop lama, tetap ada
├─ firmware/esp32/main.py      # MicroPython untuk hardware (nantinya)
└─ docs/
   ├─ index.html              # tampilan web
   ├─ style.css               # desain dan responsif
   ├─ script.js               # logika simulator + kontrol
   └─ WEB_SETUP.md            # panduan ini
```

## Jalankan lokal

1. Buka folder repository TRIWISE di VS Code.
2. Buka `docs/index.html` di Chrome, Edge, atau Firefox (double-click atau klik kanan `Reveal in File Explorer`, lalu buka).
3. Klik `+ Logam`, `+ Plastik`, atau `+ Lainnya`; tekan `MULAI`. Kamu bisa memilih `Mode otomatis` atau `Tambahkan batch demo`.
4. CSV event log dapat diunduh menggunakan tombol `↓ CSV`.

**Tidak perlu Python, ESP32, PLC, `npm`, dan tidak ada library eksternal.**

## Publikasi melalui GitHub Pages

1. Dari terminal VS Code pada root repository:
   ```bash
   git add docs/
   git commit -m "Menambahkan simulasi web TRIWISE"
   git push origin main
   ```
2. Di halaman repository GitHub, buka `Settings` → `Pages`.
3. Pada `Build and deployment`, pilih `Deploy from a branch`.
4. Pilih branch `main`, folder `/docs`, lalu `Save`.
5. Tunggu publikasi muncul di halaman `Settings → Pages`, lalu klik alamat website yang disediakan. Tautannya biasanya mengikuti pola `https://USERNAME.github.io/NAMA_REPO/`.

Catatan: GitHub Pages bersifat **publik**. Jangan memasukkan password Wi-Fi, kunci API, atau informasi rahasia ke `docs`.

## Apa yang sama dengan Python?

- Hanya **satu benda aktif** pada conveyor, sementara benda lain mengantre.
- Kecepatan default 120 piksel/detik, bisa diubah dari 50 s.d. 230.
- Klasifikasi berdasarkan sensor virtual: logam, plastik, lainnya.
- Urutan prioritas deteksi: logam → plastik → lainnya.
- Logam didorong di X=465 menuju wadah atas, plastik di X=677 menuju wadah bawah, material lainnya terus ke X=908.
- Counter bertambah **setelah benda mencapai sensor keluaran**, bukan ketika klasifikasi.
- Mode otomatis, jeda, reset, dan event log.

Fitur tambahan web: animasi tampilan modern, tombol batch demo, misi 5 benda, shortcut keyboard, ekspor CSV, layout responsif.

## Batasan

Model sensor plastik dalam website (seperti versi Tkinter) adalah **ideal untuk pengajaran**, bukan bukti sensor kapasitif dapat membedakan semua jenis plastik. Belum membaca sensor ESP32 atau mengendalikan motor/servo fisik. Angka dan animasi bukan data IoT nyata. Tidak ada penyimpanan permanen; refresh halaman mereset sesi.
