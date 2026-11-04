# Log kendala, solusi, dan tindak lanjut TRIWISE

**Periode:** Pengembangan awal hingga 3 November 2026  
**Status penting:** *Terselesaikan* berarti sudah dikonfirmasi pengguna/hasil uji; *Belum diverifikasi* berarti solusi telah dijelaskan tetapi belum ada bukti berhasil; *Terbuka* berarti diperlukan pengujian lanjutan.

| ID | Area | Kendala | Solusi / tindakan | Status |
|---|---|---|---|---|
| ISS-001 | Git / VS Code | Commit gagal: unable to auto-detect email address | Konfigurasi git config --global user.name dan user.email; jalankan kembali commit dan push | Belum diverifikasi |
| ISS-002 | Git / terminal | Pesan error: no action specified | Periksa perintah lengkap dan git status; ulangi perintah yang valid; minta tangkapan terminal jika berulang | Belum terdiagnosis |
| ISS-003 | VS Code / workspace | Untitled (Workspace) tampil di atas folder TRIWISE | File > Open Folder, pilih folder repository TRIWISE, lalu Don't Save untuk konfigurasi untitled workspace | Terselesaikan (konfirmasi pengguna) |
| ISS-004 | VS Code / struktur folder | Folder docs/ dan docs_esp32 sempat berada di tempat yang tidak sesuai | Pindahkan file web ke TRIWISE/docs; satukan dokumentasi; periksa Explorer | Terselesaikan (konfirmasi pengguna) |
| ISS-005 | Simulasi Python | Belum ada hardware ESP32 untuk menjalankan firmware | Buat simulation/main.py dengan engine Tkinter, antrian, sensor virtual, counter dan tombol kendali | Terselesaikan untuk simulasi |
| ISS-006 | Web simulator | Simulasi Tkinter tidak bisa langsung dibuka oleh browser eksternal | Implementasi ulang logika desktop ke docs/index.html, style.css, script.js | Terselesaikan untuk source web |
| ISS-007 | GitHub Pages | Apakah link eksternal GitHub Pages aktif dan dapat dibagikan | GitHub Settings > Pages > main /docs; verifikasi URL setelah deploy | Menunggu verifikasi |
| ISS-008 | Sensor plastik | Sensor kapasitif tidak spesifik mengenali semua jenis plastik | Batasi sampel, uji confusion matrix, kalibrasi jarak/ambang, pertimbangkan sensor tambahan | Terbuka - butuh hardware |
| ISS-009 | Conveyor & servo | Waktu tempuh dan sudut servo belum disesuaikan mekanik asli | Ukur jarak dan kecepatan nyata; kalibrasi nilai travel dan push serta sudut masing-masing servo | Terbuka - butuh hardware |
| ISS-010 | Counter | Potensi penghitungan ganda atau objek tidak masuk wadah pada prototype | Letakkan counter pada keluaran, gunakan deteksi tepi & debounce, verifikasi terhadap hitungan manual | Terbuka - butuh hardware |
| ISS-011 | Git / keamanan | File wifi_config.py bisa berisi SSID/password | Masukkan firmware/esp32/wifi_config.py ke .gitignore dan cek git status sebelum push | Perlu diverifikasi |
| ISS-012 | Pengujian | Keberhasilan simulasi bukan bukti kalibrasi sensor fisik | Pisahkan laporan simulasi, daftar parameter awal, dan hasil uji hardware | Terdokumentasi |

## Catatan bukti yang tidak boleh dilebihkan

- Pengguna sudah menyatakan program Python berhasil berjalan, tetapi **belum ada konfirmasi** bahwa pengaturan identitas Git dan seluruh proses push selesai tanpa error.
- Pengguna menyatakan struktur folder dan workspace VS Code sudah rapi.
- Source website telah dibuat, tetapi **status publikasi GitHub Pages masih perlu dicek**.
- Tidak ada bukti komponen ESP32, sensor, conveyor, ataupun servo sudah diuji. Tidak ada angka akurasi hardware.
- Baris `ISS-011` adalah langkah pencegahan; jangan menganggap password Wi-Fi pernah terunggah tanpa bukti.

## Cara mencatat issue baru

Tambahkan satu baris dengan tanggal, versi/commit jika tersedia, gejala yang bisa diulang, penyebab terverifikasi (atau tandai *dugaan*), solusi yang dicoba, hasil pengujian ulang, dan status. Simpan screenshot/log error jika memungkinkan, **tanpa kredensial pribadi**.
