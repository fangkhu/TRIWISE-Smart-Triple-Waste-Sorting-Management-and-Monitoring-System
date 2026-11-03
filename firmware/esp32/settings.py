"""Konfigurasi TRIWISE ESP32 klasik (ESP32-WROOM DevKit), MicroPython.
Semua GPIO input WAJIB dibatasi ke 0–3.3 V. Ubah sesuai hasil pengujian.
"""

# Input sensor digital. Aktif LOW (=0) untuk output NPN/open collector
# yang SUDAH dikondisikan aman ke GPIO 3.3 V.
SENSOR_PINS = {
    "entry": 27,          # Sensor benda masuk ke stasiun pembacaan
    "metal": 32,          # Induktif - logam
    "plastic": 33,        # Kapasitif - PROKSI plastik (perlu kalibrasi)
    "exit_metal": 13,     # Photoelectric pada wadah logam
    "exit_plastic": 14,   # Photoelectric pada wadah plastik
    "exit_other": 23,     # Photoelectric pada wadah lainnya
}
SENSOR_ACTIVE_LEVEL = {
    "entry": 0,
    "metal": 0,
    "plastic": 0,
    "exit_metal": 0,
    "exit_plastic": 0,
    "exit_other": 0,
}

# Tombol RUN/STOP ke GND; resistor pull-up internal aktif.
RUN_BUTTON_PIN = 26

# TB6612FNG channel A: PWMA, AIN1, AIN2; STBY hubungkan ke 3.3 V.
MOTOR_PWM_PIN = 25
MOTOR_IN1_PIN = 16
MOTOR_IN2_PIN = 17
MOTOR_SPEED_PERCENT = 65  # 0..100; untuk motor low voltage yang kompatibel

# 2 servo dengan sumber daya 5–6 V terpisah, GND bersama ESP32.
SERVO_METAL_PIN = 18
SERVO_PLASTIC_PIN = 19
SERVO_HOME_ANGLE = {"metal": 90, "plastic": 90}
SERVO_PUSH_ANGLE = {"metal": 125, "plastic": 125}
# Pulsa servo disetel konservatif, tetap wajib kalibrasi saat TANPA beban.
SERVO_MIN_PULSE_US = 1000
SERVO_MAX_PULSE_US = 2000

# WAKTU WAJIB dikalibrasi berdasarkan kecepatan dan jarak fisik conveyor!
SENSOR_DEBOUNCE_MS = 45
SCAN_WINDOW_MS = 300
TRAVEL_TO_METAL_PUSHER_MS = 700
TRAVEL_TO_PLASTIC_PUSHER_MS = 1300
PUSH_DURATION_MS = 430
EXIT_TIMEOUT_MS = 7000
LOOP_DELAY_MS = 10
WIFI_TIMEOUT_MS = 7000
