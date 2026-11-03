# TRIWISE — ESP32 MicroPython (tanpa PLC)

## Status dan batasan

Prototipe **awal untuk eksperimen di meja**. Semua pin mengacu pada **ESP32 DevKit klasik (ESP32-WROOM)**, bukan ESP32-C3/S3. Masukkan **satu benda setiap siklus**. Sensor kapasitif tidak secara khusus mengidentifikasi plastik; akurasi harus diuji dengan sampel yang ditetapkan. Motor, servo, dan sensor **belum diuji pada perangkat fisik**.

## Struktur file dalam repository GitHub

```text
TRIWISE/
├── firmware/
│   └── esp32/
│       ├── main.py                 # kode utama MicroPython
│       ├── settings.py             # mapping GPIO & timer
│       ├── wifi_config.example.py  # contoh konfigurasi, boleh di-commit
│       └── wifi_config.py          # buat sendiri, jangan di-commit
├── docs/
│   └── SETUP_ESP32.md
├── README.md                       # file lama, jangan dihapus
└── .gitignore                      # file lama, tambahkan pengabaian Wi-Fi
```

Tambahkan baris ini di **.gitignore** yang sudah ada: `firmware/esp32/wifi_config.py`. Bila perlu tambahkan `__pycache__/`.

## GPIO dan koneksi sinyal

| GPIO ESP32 | Fungsi | Catatan |
|---|---|---|
| 27 | Sensor benda masuk | digital 0–3,3 V |
| 32 | Sensor induktif logam | **jangan** sambung keluaran sensor 12/24 V langsung |
| 33 | Sensor kapasitif (indikator) | bukan sensor plastik khusus |
| 13 | Sensor counter wadah logam | dihitung saat benda tiba |
| 14 | Sensor counter wadah plastik | dihitung saat benda tiba |
| 23 | Sensor counter wadah lainnya | dihitung saat benda tiba |
| 26 | Tombol RUN/STOP | tombol ke GND, pull-up internal |
| 25 | TB6612 PWMA | output PWM kontrol kecepatan |
| 16 | TB6612 AIN1 | arah motor |
| 17 | TB6612 AIN2 | arah motor |
| 18 | Signal servo logam | catu servo eksternal |
| 19 | Signal servo plastik | catu servo eksternal |
| 21, 22 | Cadangan | untuk LCD I2C bila ditambahkan |

**Penting:** TB6612 `STBY` harus dibuat HIGH pada sisi logika 3,3 V; `VCC` logika sesuai modul, `VM` dan motor sesuai tegangan serta arus motor yang dipilih. TB6612 tidak cocok untuk motor dengan arus melebihi spesifikasi driver. Pasang perlindungan sumber daya, pengaman area bergerak, dan **saklar pemutus motor** fisik. Catu servo **5–6 V terpisah** (sesuai spesifikasi servo) dan sambungkan GND bersama, bukan ambil arus servo dari pin ESP32. Semua **sinyal** GPIO wajib 0–3,3 V. Sensor industri 6–36 V memerlukan *optocoupler* atau rangkaian penyesuai level yang sesuai dan diperiksa pengajar/teknisi.

## Perangkat lunak

1. Unduh firmware MicroPython yang **sesuai persis dengan varian board** dari https://micropython.org/download/esp32/ ; pasang ke ESP32 mengikuti panduan resminya, misalnya lewat Thonny (Run > Select interpreter > MicroPython ESP32 > install firmware).
2. Tetap menulis kode di **VS Code** dalam folder repository GitHub. Install Python desktop untuk menjalankan `mpremote` (bukan untuk menjalankan `main.py`).
3. Di terminal VS Code: `python -m pip install mpremote` (atau `py -m pip install mpremote` di Windows).
4. Salin `wifi_config.example.py` menjadi `wifi_config.py`, lalu isi Wi-Fi 2,4 GHz setempat.
5. Dengan board terhubung via USB, jalankan perintah berikut dari folder repository (ganti `COM5` sesuai Device Manager):

```powershell
mpremote connect COM5 fs cp firmware/esp32/settings.py :settings.py
mpremote connect COM5 fs cp firmware/esp32/wifi_config.py :wifi_config.py
mpremote connect COM5 fs cp firmware/esp32/main.py :main.py
mpremote connect COM5 reset
```

> `main.py` pada ESP32 akan berjalan saat boot/restart. **Jangan** menjalankan kode MicroPython ini dengan `python main.py` di laptop karena modul `machine` hanya tersedia pada board. Perintah `mpremote` perlu akses port yang tidak sedang dipakai Thonny/Serial Monitor.

## Tahap pengujian (urut dan bertahap)

1. **Tanpa motor/aktuator terpasang**, uji dengan board dan sinyal sensor yang sudah dikondisikan ke 3,3 V: baca nilai sensor satu per satu. Bila tidak aktif ketika benda berada di depan sensor, sesuaikan `SENSOR_ACTIVE_LEVEL`.
2. Uji servo dalam kondisi **tanpa beban**, periksa arah `SERVO_HOME_ANGLE`, `SERVO_PUSH_ANGLE` dan rentang sudut agar tidak menabrak rangka.
3. Pasang conveyor mini yang sudah diberi perlindungan dan uji tombol START/STOP serta arah putaran. **Motor OFF saat boot.**
4. Tempatkan sensor **entry, metal, plastic berdekatan** pada stasiun klasifikasi. Sesuaikan `SCAN_WINDOW_MS` agar bahan terbaca sebelum keluar dari area sensor.
5. Ukur waktu dari akhir pembacaan sampai benda tiba di pendorong logam dan plastik; sesuaikan `TRAVEL_TO_METAL_PUSHER_MS` dan `TRAVEL_TO_PLASTIC_PUSHER_MS`. Masukkan **satu benda tiap siklus**.
6. Pasang sensor counter tepat pada jalur **masuk wadah**, lalu uji apakah ketiganya menambah counter **sekali per satu benda**. Bila sebuah benda tidak tertangkap sensor keluaran hingga timeout, program **menghentikan motor**.
7. Saat Wi-Fi tersambung, lihat URL `http://<IP-ESP32>/` yang tercetak di serial monitor. Buka dari ponsel/laptop pada jaringan yang sama; `/api` mengembalikan JSON. Dashboard **hanya baca**.

### Cara membaca status

- `IDLE`: siap menerima benda.
- `SCAN`: merekam keluaran sensor logam/kapasitif selama jendela waktu.
- `WAIT_PUSH`: menunggu benda berada di depan pendorong.
- `PUSHING`: servo bergerak sesaat.
- `WAIT_EXIT`: menunggu benda sampai di salah satu sensor keluaran.
- `WAIT_CLEAR`: menunggu sensor masuk tidak mendeteksi benda lagi.
- `ALARM`: benda tidak sampai ke salah satu counter tepat waktu; motor berhenti. Periksa jalur, tekan tombol untuk mereset alarm, lalu tekan lagi untuk mulai.

## Konsep klasifikasi

- Jika sensor **logam** aktif selama scan ⇒ kategori **logam**.
- Jika tidak logam dan sensor **kapasitif** aktif selama scan ⇒ kategori **indikasi plastik**.
- Jika keduanya tidak aktif ⇒ **lainnya**.

Sensor kapasitif juga bisa aktif untuk kaca, kertas, cairan, dan beragam nonlogam. Kategori plastik **tidak valid untuk pemilahan sampah campuran sesungguhnya** tanpa perbaikan sensor/algoritma dan pengujian. Semua klasifikasi berbasis lokasi sampel, bukan identifikasi material spesifik.

## Counter, IoT, dan keterbatasan

- Tiga counter bertambah karena **sensor keluaran wadah** aktif, bukan saat klasifikasi.
- Hasil tetap berjalan bila Wi-Fi gagal tersambung; dashboard menjadi tidak tersedia sampai restart dengan koneksi yang baik.
- Data counter saat ini disimpan di **RAM**, sehingga **reset listrik mengembalikan hitungan ke nol**. Penyimpanan permanen bisa menjadi pengembangan berikutnya (jangan tulis flash setiap benda tanpa pertimbangan umur flash).
- Dashboard hanya tersedia pada **jaringan Wi-Fi lokal**; jangan meneruskan port 80 ke internet. Belum dilengkapi autentikasi pengguna.
- Sensor counter yang mengirim sinyal saat fase `SCAN`, atau sampah yang dimasukkan bertumpuk, tidak ditangani oleh versi pertama ini.

## Simpan ke GitHub

```bash
git status
git add firmware/esp32/main.py firmware/esp32/settings.py firmware/esp32/wifi_config.example.py docs/SETUP_ESP32.md .gitignore
git commit -m "Menambahkan firmware MicroPython TRIWISE untuk ESP32"
git push origin main
```

Pastikan `wifi_config.py` **tidak masuk** di hasil `git status`/commit.
