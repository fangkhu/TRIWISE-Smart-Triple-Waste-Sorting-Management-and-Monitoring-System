"""TRIWISE - pemilah 3 jenis sampah, ESP32 + MicroPython.

Fitur:
- 1 motor conveyor (via driver TB6612FNG)
- sensor masuk + sensor induktif dan kapasitif
- 2 servo pendorong, jalur 'lainnya' tanpa pendorong
- 3 sensor counter pada KELUARAN wadah (counter sekali per benda)
- tombol RUN/STOP; motor selalu OFF setelah ESP32 boot
- dashboard monitor lokal http://IP_ESP32/ serta /api

BATASAN: benda harus dimasukkan satu per satu, sensor klasifikasi harus
berdekatan di stasiun masuk, dan waktunya harus dikalibrasi. Sensor
kapasitif TIDAK mengidentifikasi plastik secara pasti.
"""

from machine import Pin, PWM
import network
import socket
import time
import settings as cfg

try:
    import ujson as json
except ImportError:
    import json


class DebouncedInput:
    """Mendeteksi perubahan stabil; event True hanya saat baru aktif."""
    def __init__(self, pin_number, active_level=0, debounce_ms=45):
        self.pin = Pin(pin_number, Pin.IN, Pin.PULL_UP)
        self.active_level = active_level
        self.debounce_ms = debounce_ms
        self.raw = self._read()
        self.active = self.raw
        self.last_raw_change = time.ticks_ms()

    def _read(self):
        return self.pin.value() == self.active_level

    def update(self, now):
        current = self._read()
        if current != self.raw:
            self.raw = current
            self.last_raw_change = now
        if self.active != self.raw and time.ticks_diff(now, self.last_raw_change) >= self.debounce_ms:
            self.active = self.raw
            return self.active
        return None


class Conveyor:
    def __init__(self):
        self.in1 = Pin(cfg.MOTOR_IN1_PIN, Pin.OUT, value=0)
        self.in2 = Pin(cfg.MOTOR_IN2_PIN, Pin.OUT, value=0)
        self.pwm = PWM(Pin(cfg.MOTOR_PWM_PIN), freq=1000, duty_u16=0)

    def start(self):
        percent = max(0, min(100, cfg.MOTOR_SPEED_PERCENT))
        self.in1.value(1)
        self.in2.value(0)
        self.pwm.duty_u16(percent * 65535 // 100)

    def stop(self):
        self.pwm.duty_u16(0)
        self.in1.value(0)
        self.in2.value(0)


class ServoPusher:
    def __init__(self, pin_number, home_angle, push_angle):
        self.pwm = PWM(Pin(pin_number), freq=50)
        self.home_angle = home_angle
        self.push_angle = push_angle
        self.home()

    def set_angle(self, angle):
        angle = max(0, min(180, angle))
        width_us = cfg.SERVO_MIN_PULSE_US + (
            cfg.SERVO_MAX_PULSE_US - cfg.SERVO_MIN_PULSE_US
        ) * angle // 180
        self.pwm.duty_ns(width_us * 1000)

    def home(self):
        self.set_angle(self.home_angle)

    def push(self):
        self.set_angle(self.push_angle)


class Triwise:
    def __init__(self):
        self.motor = Conveyor()
        self.metal_servo = ServoPusher(
            cfg.SERVO_METAL_PIN,
            cfg.SERVO_HOME_ANGLE["metal"], cfg.SERVO_PUSH_ANGLE["metal"]
        )
        self.plastic_servo = ServoPusher(
            cfg.SERVO_PLASTIC_PIN,
            cfg.SERVO_HOME_ANGLE["plastic"], cfg.SERVO_PUSH_ANGLE["plastic"]
        )
        self.inputs = {}
        for name, pin in cfg.SENSOR_PINS.items():
            self.inputs[name] = DebouncedInput(
                pin, cfg.SENSOR_ACTIVE_LEVEL[name], cfg.SENSOR_DEBOUNCE_MS
            )
        self.button = DebouncedInput(cfg.RUN_BUTTON_PIN, 0, cfg.SENSOR_DEBOUNCE_MS)
        self.running = False
        self.phase = "IDLE"
        self.expected = "-"
        self.last_result = "Belum ada sampah"
        self.error = ""
        self.counts = {"metal": 0, "plastic": 0, "other": 0}
        self.mismatch_count = 0
        self.scan_metal_seen = False
        self.scan_plastic_seen = False
        self.scan_at = 0
        self.classified_at = 0
        self.push_at = 0
        self.push_started = 0
        self.servo_in_use = None

    def safe_stop(self):
        self.running = False
        self.motor.stop()
        self.metal_servo.home()
        self.plastic_servo.home()
        self.servo_in_use = None
        self.phase = "IDLE"
        self.expected = "-"

    def on_button(self):
        if self.error:
            self.error = ""
            self.safe_stop()
            print("Alarm direset. Periksa jalur; tekan lagi untuk START.")
        elif self.running:
            self.safe_stop()
            print("STOP: conveyor berhenti.")
        elif self.inputs["entry"].active:
            print("START ditolak: keluarkan benda dari sensor masuk dahulu.")
        else:
            self.running = True
            self.phase = "IDLE"
            self.motor.start()
            print("RUN: conveyor bergerak.")

    def fail(self, message):
        self.safe_stop()
        self.error = message
        self.last_result = "ERROR: " + message
        print(self.last_result)

    def sample_classifiers(self):
        # Metal diprioritaskan jika kedua sensor mendeteksi material.
        self.scan_metal_seen = self.scan_metal_seen or self.inputs["metal"].active
        self.scan_plastic_seen = self.scan_plastic_seen or self.inputs["plastic"].active

    def classify(self, now):
        if self.scan_metal_seen:
            self.expected = "metal"
            delay = cfg.TRAVEL_TO_METAL_PUSHER_MS
        elif self.scan_plastic_seen:
            self.expected = "plastic"
            delay = cfg.TRAVEL_TO_PLASTIC_PUSHER_MS
        else:
            self.expected = "other"
            delay = 0
        self.classified_at = now
        self.push_at = time.ticks_add(now, delay)
        self.phase = "WAIT_EXIT" if self.expected == "other" else "WAIT_PUSH"
        print("Klasifikasi:", self.expected)

    def check_exit(self, events):
        # Dipanggil hanya ketika satu benda sedang diproses.
        for sensor_name, category in (
            ("exit_metal", "metal"),
            ("exit_plastic", "plastic"),
            ("exit_other", "other"),
        ):
            if events[sensor_name] is True:
                self.counts[category] += 1
                if category != self.expected:
                    self.mismatch_count += 1
                    self.last_result = "Salah jalur: prediksi %s, keluaran %s" % (
                        self.expected, category
                    )
                else:
                    self.last_result = "Berhasil dihitung: " + category
                self.metal_servo.home()
                self.plastic_servo.home()
                self.servo_in_use = None
                self.phase = "WAIT_CLEAR"
                self.expected = "-"
                print(self.last_result, "| Counter:", self.counts)
                return True
        return False

    def step(self):
        now = time.ticks_ms()
        events = {}
        for name, sensor in self.inputs.items():
            events[name] = sensor.update(now)
        if self.button.update(now) is True:
            self.on_button()

        if not self.running:
            return

        if self.phase == "IDLE":
            if events["entry"] is True:
                self.phase = "SCAN"
                self.scan_at = now
                self.scan_metal_seen = False
                self.scan_plastic_seen = False
                self.sample_classifiers()
                print("Benda masuk: membaca material...")
            return

        if self.phase == "SCAN":
            self.sample_classifiers()
            if time.ticks_diff(now, self.scan_at) >= cfg.SCAN_WINDOW_MS:
                self.classify(now)
            return

        if self.phase in ("WAIT_PUSH", "PUSHING", "WAIT_EXIT"):
            # Konfirmasi dihitung di wadah, bukan saat sensor klasifikasi aktif.
            if self.check_exit(events):
                return
            if time.ticks_diff(now, self.classified_at) >= cfg.EXIT_TIMEOUT_MS:
                self.fail("Benda tidak terdeteksi di salah satu wadah (timeout)")
                return

        if self.phase == "WAIT_PUSH" and time.ticks_diff(now, self.push_at) >= 0:
            self.servo_in_use = self.metal_servo if self.expected == "metal" else self.plastic_servo
            self.servo_in_use.push()
            self.push_started = now
            self.phase = "PUSHING"
        elif self.phase == "PUSHING":
            if time.ticks_diff(now, self.push_started) >= cfg.PUSH_DURATION_MS:
                self.servo_in_use.home()
                self.servo_in_use = None
                self.phase = "WAIT_EXIT"
        elif self.phase == "WAIT_CLEAR":
            # Jangan membaca benda baru sampai sensor masuk benar-benar bebas.
            if not self.inputs["entry"].active:
                self.phase = "IDLE"

    def snapshot(self):
        return {
            "running": self.running,
            "phase": self.phase,
            "expected": self.expected,
            "metal": self.counts["metal"],
            "plastic": self.counts["plastic"],
            "other": self.counts["other"],
            "total": sum(self.counts.values()),
            "misrouted": self.mismatch_count,
            "last_result": self.last_result,
            "error": self.error,
        }


def setup_web():
    try:
        from wifi_config import SSID, PASSWORD
    except ImportError:
        print("Tidak ada wifi_config.py: dashboard dinonaktifkan.")
        return None

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(SSID, PASSWORD)
        started = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), started) > cfg.WIFI_TIMEOUT_MS:
                print("Wi-Fi belum tersambung: kontrol lokal tetap berjalan.")
                return None
            time.sleep_ms(100)
    print("Dashboard TRIWISE: http://%s/" % wlan.ifconfig()[0])
    try:
        server = socket.socket()
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", 80))
        server.listen(2)
        server.settimeout(0.001)
        return server
    except OSError as exc:
        print("Dashboard tidak dapat dibuka:", exc)
        return None


def render_dashboard(data):
    running = "RUN" if data["running"] else "STOP"
    if data["error"]:
        running = "ALARM"
    return """<!doctype html><html lang="id"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="3"><title>TRIWISE IoT</title></head>
<body style="font-family:Arial,sans-serif;max-width:650px;margin:25px auto;padding:12px;background:#101827;color:white">
<h1>TRIWISE</h1><p>Smart Waste Sorting | Dashboard LAN (auto-refresh 3 detik)</p>
<h2>Status: {status}</h2><p>Fase: {phase} | Prediksi: {expected}</p>
<div style="background:#253045;padding:15px;border-radius:10px">
<h2>Logam: {metal}</h2><h2>Plastik: {plastic}</h2><h2>Lainnya: {other}</h2>
<hr><h2>TOTAL: {total}</h2></div>
<p>Salah jalur: {misrouted}</p><p>Hasil terakhir: {last_result}</p>
<p>Alarm: {error}</p><p><small>Monitoring hanya-baca. START/STOP lewat tombol fisik.</small></p>
<p><a href="/api" style="color:#7dd3fc">Data JSON /api</a></p>
</body></html>""".format(
        status=running, phase=data["phase"], expected=data["expected"],
        metal=data["metal"], plastic=data["plastic"], other=data["other"],
        total=data["total"], misrouted=data["misrouted"],
        last_result=data["last_result"], error=data["error"] or "Tidak ada",
    )


def serve_once(server, app):
    if server is None:
        return
    try:
        client, _addr = server.accept()
    except OSError:
        return  # Tidak ada permintaan HTTP saat ini.
    try:
        client.settimeout(0.05)
        request = client.recv(512)
        if request.startswith(b"GET /api "):
            content_type = "application/json"
            body = json.dumps(app.snapshot())
        else:
            content_type = "text/html; charset=utf-8"
            body = render_dashboard(app.snapshot())
        header = (
            "HTTP/1.0 200 OK\r\nContent-Type: %s\r\n"
            "Cache-Control: no-store\r\nConnection: close\r\n\r\n" % content_type
        )
        client.sendall(header.encode())
        client.sendall(body.encode())
    except OSError:
        pass
    finally:
        client.close()


def main():
    app = Triwise()  # Motor OFF dan servo HOME saat inisialisasi.
    server = setup_web()
    print("TRIWISE SIAGA. Tekan tombol GPIO26->GND untuk START/STOP.")
    try:
        while True:
            app.step()
            serve_once(server, app)
            time.sleep_ms(cfg.LOOP_DELAY_MS)
    finally:
        app.safe_stop()
        if server is not None:
            server.close()
        print("TRIWISE berhenti aman.")


if __name__ == "__main__":
    main()
