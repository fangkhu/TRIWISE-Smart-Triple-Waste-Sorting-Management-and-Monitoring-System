# TRIWISE — Dokumentasi pengujian & pra-kalibrasi

**Tanggal penyusunan:** 3 November 2026  
**Lingkup:** `simulation/main.py`, `docs/script.js`, dan konfigurasi awal `firmware/esp32/settings.py` dari pengembangan TRIWISE.

> **PENTING:** Belum ada kalibrasi sensor atau aktuator fisik. Nilai piksel, kecepatan virtual, sudut servo, durasi, dan logika deteksi plastik dalam berkas ini merupakan **parameter simulasi atau pengaturan awal firmware**, bukan data pengukuran alat.

## File

| File | Fungsi |
|---|---|
| `parameter_pra_kalibrasi.csv` | Nilai aktual yang tertulis di kode simulasi/konfigurasi firmware; setiap baris menyebutkan sumber dan satuan. |
| `uji_parameter_virtual.csv` | Hasil uji respons sensor ideal, alur pendorong, dan waktu ke wadah virtual pada tiga kecepatan. **Bukan** kalibrasi sensor fisik. |
| `hasil_uji_simulasi.csv` | Bukti pengujian ulang logika simulator Python dan JavaScript; tidak termasuk validasi sensor fisik. |
| `template_kalibrasi_hardware.csv` | Rancangan pengujian sensor, counter, motor, servo, keamanan, dan IoT. Kolom hasil ukur sengaja kosong. |
| `log_kendala_solusi.csv` | Log kendala nyata, tindak lanjut, risiko, status, dan bukti dari pembahasan pengembangan. |
| `LOG_KENDALA_SOLUSI.md` | Versi terbaca di GitHub untuk log kendala dan solusi. |
| `METODOLOGI_PENGUJIAN.md` | Metode uji, definisi metrik, batasan, dan cara mencatat data. |
| `TRIWISE_Pengujian_Kalibrasi_Log.xlsx` | Workbook ringkas untuk pengolahan / presentasi di Excel. |

## Yang sudah teruji secara perangkat lunak

- **Desktop Python**: uji bawaan menghasilkan counter **2 logam, 1 plastik, 1 lainnya**; jeda dan reset lolos.
- **Web JavaScript**: menjalankan kelas `TriwiseSimulator` pada batch uji deterministik menghasilkan **2 logam, 2 plastik, 2 lainnya**; jeda dan reset lolos.
- Uji tambahan pada kecepatan virtual 50 dan 230 px/s menghasilkan jumlah yang diharapkan. Sembilan uji sensor/aktuator virtual pada kecepatan 50, 120, dan 230 px/s dicatat di `uji_parameter_virtual.csv`.

Hasil tersebut **tidak boleh** disebut akurasi sensor fisik atau keberhasilan pemilahan fisik.

## Cara memakai

1. Salin folder `testing/` ke root repository TRIWISE (sejajar `simulation/`, `firmware/`, `docs/`).
2. Untuk uji bawaan Python, jalankan: `python simulation/main.py --self-test` dari root repository.
3. Lanjutkan mengembangkan dan mencatat kendala pada `log_kendala_solusi.csv` / `.md`.
4. Saat sensor/aktuator tersedia, isi `template_kalibrasi_hardware.csv` berdasarkan pengukuran nyata (tanggal, sampel, hasil, satuan).
5. Perbarui file Excel dan berkas CSV agar tidak berbeda versi.

**Prinsip ilmiah:** hasil ukur *belum tersedia* berbeda dari nilai *0*. Jangan mengisi hasil kosong dengan nol atau angka simulasi.
