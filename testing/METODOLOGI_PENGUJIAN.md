# Metodologi pengujian dan kalibrasi TRIWISE

## A. Status bukti

- **TERUJI SIMULASI** = hasil dieksekusi oleh program perangkat lunak yang ada pada repository.
- **PARAMETER RANCANGAN** = nilai default kode, asumsi posisi virtual, atau setelan awal firmware; belum diukur.
- **BELUM DIUJI HARDWARE** = perlu alat fisik, sampel nyata, serta prosedur keselamatan.

Jangan menjadikan akurasi klasifikasi 100% dalam simulasi sebagai kesimpulan performa mesin. Model saat ini menggunakan jenis material yang sudah diketahui (`actual`) untuk menghasilkan sinyal sensor virtual yang ideal.

## B. Parameter program yang telah dikonfirmasi

1. Desktop & web: satu benda aktif pada conveyor dalam satu waktu; benda lain menunggu di antrean.
2. Sensor masuk menandai benda baru. Sensor induktif virtual bereaksi pada `metal`; indikator plastik virtual pada `plastic`; sisanya masuk kategori `other`.
3. Logam diprioritaskan apabila dua indikator bernilai aktif (aturan kode), meski kondisi ini tidak muncul secara natural pada dataset ideal.
4. Pendorong logam berada pada X=465 px dan plastik X=677 px; material lain lewat sampai X=908 px. Kecepatan awal 120 px/s, rentang slider desktop 50–230 px/s.
5. Counter bertambah ketika benda sampai keluaran masing-masing, bukan ketika baru dideteksi.
6. Terdapat jeda 0,3 s antar benda dan lampu indikator aktif 0,65 s pada simulasi.
7. Firmware ESP32 yang disiapkan memiliki parameter awal 700 ms (logam), 1300 ms (plastik), 430 ms (dorong), PWM motor 65%, sudut 90°/125°. Semuanya hanya estimasi sebelum kalibrasi.

## C. Langkah uji simulasi yang dapat direproduksi

**Python desktop:**

```bash
python simulation/main.py --self-test
```

Hasil yang diharapkan: `PASS: klasifikasi, dua pendorong, 3 counter, jeda, dan reset.` serta counter 2/1/1 sebelum reset.

**Web:** Buka `docs/index.html`, jalankan batch terkontrol 2 logam + 2 plastik + 2 lainnya dan tunggu sampai antrean kosong. Jumlah akhir harus 2/2/2. Jangan gunakan mode acak jika ingin membandingkan data deterministik.

Perhitungan waktu pada kode memakai `dt` per langkah, sehingga total durasi observasi dapat sedikit berbeda tergantung frekuensi frame. Angka durasi di file CSV bukan hasil pengukuran mekanik.

## D. Rencana kalibrasi hardware saat tersedia

1. Catat identitas alat, model sensor, objek uji, kondisi sampel (kering/basah), ukuran sampel, dan jumlah ulangan.
2. Kalibrasi sensor masuk dan sensor logam pada beberapa jarak, ulangi untuk bahan berbeda.
3. Untuk sensor kapasitif, uji **plastik, kertas, karton, kaca, dan material lainnya**; catat sensitivitas serta salah klasifikasi. Kapasitif bukan pendeteksi plastik universal.
4. Uji counter keluaran dengan jumlah benda manual yang diketahui dan lihat apakah sinyal memicu hitungan ganda.
5. Ukur jarak stasiun klasifikasi hingga masing-masing pendorong, lalu ukur kecepatan **cm/s** dan waktu tempuh sebenarnya; jangan menyalin nilai **px/s** ke firmware.
6. Uji sudut servo tanpa beban lebih dahulu, kemudian dengan benda ringan; ukur keberhasilan masuk wadah masing-masing.
7. Uji tombol berhenti, respons saat listrik hilang, serta stabilitas sinyal dan catu daya. Gunakan pembatas/antarmuka tegangan yang sesuai untuk input 3,3 V ESP32.
8. Uji sampel yang berbeda secara acak, tetapi catat label kategori sebenarnya terlebih dahulu (*ground truth*).

## E. Metrik & rumus

- **Ketepatan counter (%)** = `(jumlah benda yang tercatat benar / jumlah benda aktual) × 100%` — catat juga jumlah hitungan ganda dan yang terlewat.
- **Akurasi klasifikasi (%)** = `(jumlah prediksi kategori benar / jumlah benda uji) × 100%`.
- **Keberhasilan sortir fisik (%)** = `(jumlah benda masuk wadah yang benar / jumlah benda uji) × 100%`.
- **Rata-rata waktu tempuh (ms)** = `jumlah seluruh waktu tempuh (ms) / jumlah pengamatan`.
- **Kecepatan conveyor (cm/s)** = `jarak tempuh (cm) / waktu tempuh (s)`.

Laporan hasil fisik harus membedakan salah klasifikasi, salah dorong, dan kegagalan sensor counter, serta mencatat ketidakpastian/variasi pengukuran jika relevan.

## F. Status sampai 3 November 2026

- **Selesai**: uji logika simulator Python dan mesin logika JavaScript pada skenario tercatat.
- **Belum dikerjakan**: kalibrasi sensor induktif/kapasitif nyata, motor, servo, counter fisik, integrasi ESP32, akurasi pemilahan fisik.
- **Risiko utama**: sensor kapasitif bukan pengenal jenis plastik yang selektif.

## G. Data sensor dan aktuator **virtual** dari pengujian ulang

Berkas `uji_parameter_virtual.csv` mengukur lama proses benda dari pertama kali dimunculkan sampai counter keluaran bertambah. Pengukuran dilakukan di **mesin simulasi**, menggunakan langkah waktu `dt=0,04 s`. Contoh pada kecepatan virtual 120 px/s: logam **3,52 s**, plastik **5,24 s**, dan lainnya **6,72 s**. Ini adalah waktu animasi, **bukan detik hasil pengukuran conveyor fisik**. Nilai 0 dan 1 pada sensor virtual berasal dari label bahan yang dimasukkan, bukan hasil sensor kapasitif/induktif nyata.
