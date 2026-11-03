"""TRIWISE - simulasi visual pemilahan sampah 3 kategori.

Jalankan pada laptop (Python 3.9+):
    python simulation/main.py

Uji logika tanpa membuka jendela:
    python simulation/main.py --self-test

Tidak memerlukan ESP32, PLC, sensor, Wi-Fi, atau pustaka pihak ketiga.
GUI menggunakan Tkinter (umumnya sudah ada pada Python Windows).

ASUMSI SIMULASI:
- Hanya satu benda berada pada conveyor pada satu waktu.
- Identifikasi material bersifat IDEAL untuk kebutuhan demonstrasi.
- Sensor induktif mendeteksi logam; sensor plastik disimulasikan
  positif pada sampel plastik. Pada hardware, sensor kapasitif TIDAK
  mampu membedakan semua jenis plastik dari semua material lain.
- Counter bertambah saat benda benar-benar mencapai jalur keluaran.
- Dua servo mendorong logam/plastik, sedangkan 'lainnya' terus maju.
"""

import random
import sys
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional


# ------------------------------ Tata letak ------------------------------
BELT_Y = 198.0
ENTRY_X = 104.0
CLASSIFIER_X = 265.0
METAL_PUSHER_X = 465.0
PLASTIC_PUSHER_X = 677.0
OTHER_EXIT_X = 908.0
METAL_EXIT_Y = 110.0
PLASTIC_EXIT_Y = 282.0

CATEGORY_NAMES = {
    "metal": "Logam",
    "plastic": "Plastik",
    "other": "Lainnya",
}


@dataclass
class WasteItem:
    """Satu benda di conveyor virtual."""

    actual: str
    x: float = ENTRY_X
    y: float = BELT_Y
    classified: bool = False
    predicted: Optional[str] = None
    phase: str = "conveyor"  # conveyor | push_metal | push_plastic


class TriwiseSimulator:
    """Logika simulasi yang terpisah dari GUI, sehingga dapat diuji otomatis."""

    def __init__(self):
        self.running = False
        self.auto_mode = False
        self.speed = 120.0  # piksel per detik pada belt virtual
        self.auto_interval = 1.0
        self.elapsed = 0.0
        self.next_allowed_start = 0.0
        self.last_spawn_at = -999.0
        self.active: Optional[WasteItem] = None
        self.queue: Deque[str] = deque()
        self.counts: Dict[str, int] = {k: 0 for k in CATEGORY_NAMES}
        self.last_result = "Belum ada benda yang disortir"
        self.status = "Sistem siap. Tambahkan benda, lalu tekan MULAI."
        self.events: Deque[str] = deque(maxlen=80)
        self.flash_until: Dict[str, float] = {}
        self.actuator: Optional[str] = None
        self._write_log("Simulator siap. Output awal motor dan pendorong OFF.")

    def _write_log(self, message: str):
        m = int(self.elapsed // 60)
        s = self.elapsed - m * 60
        self.events.append(f"[{m:02d}:{s:04.1f}] {message}")

    def _flash(self, sensor: str):
        self.flash_until[sensor] = self.elapsed + 0.65

    def sensor_active(self, sensor: str) -> bool:
        return self.elapsed < self.flash_until.get(sensor, -1.0)

    def add(self, category: str):
        if category not in CATEGORY_NAMES:
            raise ValueError("Kategori tidak dikenal: " + str(category))
        self.queue.append(category)
        self.status = f"{CATEGORY_NAMES[category]} masuk antrean ({len(self.queue)} benda)."
        self._write_log("Antrian masuk: " + CATEGORY_NAMES[category])

    def start(self):
        if not self.running:
            self.running = True
            self.status = "Conveyor ON. Menunggu benda atau memproses antrean."
            self._write_log("Conveyor ON")

    def pause(self):
        if self.running:
            self.running = False
            self.status = "Conveyor OFF / simulasi dijeda."
            self._write_log("Conveyor OFF (jeda)")

    def reset(self):
        self.pause()
        self.elapsed = 0.0
        self.active = None
        self.queue.clear()
        self.counts = {k: 0 for k in CATEGORY_NAMES}
        self.last_spawn_at = -999.0
        self.next_allowed_start = 0.0
        self.last_result = "Belum ada benda yang disortir"
        self.status = "Semua counter dan antrean telah direset."
        self.flash_until.clear()
        self.actuator = None
        self.events.clear()
        self._write_log("Reset selesai: seluruh counter = 0; conveyor OFF")

    def _spawn(self, category: str):
        self.active = WasteItem(actual=category)
        self.last_spawn_at = self.elapsed
        self._flash("entry")
        self.status = "Benda masuk conveyor: " + CATEGORY_NAMES[category]
        self._write_log("Sensor masuk: benda baru terdeteksi")

    def _classify(self, item: WasteItem):
        # Simulasi pembacaan sensor induktif + indikator plastik ideal.
        metal_detected = item.actual == "metal"
        plastic_detected = item.actual == "plastic"

        if metal_detected:
            self._flash("metal")
        if plastic_detected:
            self._flash("plastic")

        # Prioritas logam apabila kedua indikator aktif (sesuai firmware).
        if metal_detected:
            item.predicted = "metal"
        elif plastic_detected:
            item.predicted = "plastic"
        else:
            item.predicted = "other"

        item.classified = True
        self.status = "Hasil klasifikasi: " + CATEGORY_NAMES[item.predicted]
        self._write_log("Klasifikasi -> " + CATEGORY_NAMES[item.predicted])

    def _finish(self, category: str):
        # Menghitung SATU kali saat benda tiba di jalur keluaran.
        self._flash("out_" + category)
        self.counts[category] += 1
        self.last_result = "Benda masuk wadah " + CATEGORY_NAMES[category]
        self.status = self.last_result + "; counter +1"
        self._write_log(self.last_result + "; counter +1")
        self.active = None
        self.actuator = None
        self.next_allowed_start = self.elapsed + 0.3

    def step(self, dt: float):
        """Perbarui simulasi; dipanggil berulang oleh GUI atau pengujian."""
        if not self.running or dt <= 0:
            return
        self.elapsed += dt

        item = self.active
        if item is None:
            if self.elapsed < self.next_allowed_start:
                return
            if self.queue:
                self._spawn(self.queue.popleft())
            elif self.auto_mode and self.elapsed - self.last_spawn_at >= self.auto_interval:
                self._spawn(random.choice(tuple(CATEGORY_NAMES)))
            return

        # Penggerak belt bergerak sepanjang sumbu X.
        if item.phase == "conveyor":
            item.x += self.speed * dt

            if not item.classified and item.x >= CLASSIFIER_X:
                self._classify(item)

            if item.predicted == "metal" and item.x >= METAL_PUSHER_X:
                item.x = METAL_PUSHER_X
                item.phase = "push_metal"
                self.actuator = "metal"
                self.status = "Servo logam AKTIF: mendorong ke wadah logam"
                self._write_log("Servo pendorong LOGAM ON")
            elif item.predicted == "plastic" and item.x >= PLASTIC_PUSHER_X:
                item.x = PLASTIC_PUSHER_X
                item.phase = "push_plastic"
                self.actuator = "plastic"
                self.status = "Servo plastik AKTIF: mendorong ke wadah plastik"
                self._write_log("Servo pendorong PLASTIK ON")
            elif item.predicted == "other" and item.x >= OTHER_EXIT_X:
                self._finish("other")

        elif item.phase == "push_metal":
            item.y -= self.speed * 1.65 * dt
            if item.y <= METAL_EXIT_Y:
                self._finish("metal")

        elif item.phase == "push_plastic":
            item.y += self.speed * 1.65 * dt
            if item.y >= PLASTIC_EXIT_Y:
                self._finish("plastic")

    @property
    def total(self):
        return sum(self.counts.values())


def self_test():
    """Uji logika counter, klasifikasi, dan penghentian tanpa perangkat/GUI."""
    engine = TriwiseSimulator()
    engine.add("metal")
    engine.add("plastic")
    engine.add("other")
    engine.add("metal")
    engine.start()
    for _ in range(2000):
        engine.step(0.04)
        if engine.total == 4:
            break
    assert engine.counts == {"metal": 2, "plastic": 1, "other": 1}, engine.counts
    assert engine.active is None and not engine.queue
    engine.pause()
    before = engine.elapsed
    engine.step(2.0)
    assert engine.elapsed == before, "Jeda tidak bekerja"
    engine.reset()
    assert engine.total == 0 and engine.active is None and not engine.running
    print("PASS: klasifikasi, dua pendorong, 3 counter, jeda, dan reset.")
    print("Counter sebelum reset: metal=2, plastic=1, other=1")


# --------------------------------- GUI ----------------------------------
def launch_gui():
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError as exc:
        print("Tkinter tidak tersedia. Instal Python dari python.org dengan opsi Tcl/Tk.")
        raise SystemExit(1) from exc

    BG = "#0b1220"
    PANEL = "#132034"
    PANEL_2 = "#18283e"
    TEXT = "#edf4fd"
    MUTED = "#9bb0c6"
    GRID = "#283d55"
    GREEN = "#20c997"
    RED = "#f07178"
    BLUE = "#49b4f2"
    ORANGE = "#f5b858"
    MATERIAL_COLORS = {"metal": BLUE, "plastic": ORANGE, "other": "#a9b6c7"}

    sim = TriwiseSimulator()
    root = tk.Tk()
    root.title("TRIWISE | Simulasi Pemilahan Sampah 3 Kategori")
    root.geometry("1100x805")
    root.minsize(1060, 720)
    root.configure(bg=BG)

    # ------------------------------ Header ------------------------------
    header = tk.Frame(root, bg=BG)
    header.pack(fill="x", padx=22, pady=(9, 5))
    tk.Label(header, text="TRIWISE", font=("Segoe UI", 23, "bold"), fg=TEXT, bg=BG).pack(side="left")
    tk.Label(header, text="  SIMULATOR SORTIR SAMPAH • TANPA HARDWARE",
             font=("Segoe UI", 10), fg=MUTED, bg=BG).pack(side="left", pady=9)
    state_label = tk.Label(header, text="● CONVEYOR OFF", font=("Segoe UI", 10, "bold"),
                           fg=RED, bg=PANEL, padx=14, pady=7)
    state_label.pack(side="right")

    # ------------------------------ Counter -----------------------------
    stats = tk.Frame(root, bg=BG)
    stats.pack(fill="x", padx=19, pady=(1, 6))
    counter_labels = {}
    for i, (key, label, color) in enumerate([
        ("metal", "SAMPAH LOGAM", BLUE),
        ("plastic", "SAMPAH PLASTIK", ORANGE),
        ("other", "SAMPAH LAINNYA", "#abbad0"),
        ("total", "TOTAL TERSORTIR", GREEN),
    ]):
        card = tk.Frame(stats, bg=PANEL, padx=16, pady=7)
        card.grid(row=0, column=i, sticky="nsew", padx=4)
        stats.grid_columnconfigure(i, weight=1)
        tk.Label(card, text=label, fg=MUTED, bg=PANEL,
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x")
        value = tk.Label(card, text="0", fg=color, bg=PANEL,
                         font=("Segoe UI", 28, "bold"), anchor="w")
        value.pack(fill="x", pady=(4, 0))
        counter_labels[key] = value

    # ------------------------------ Conveyor ----------------------------
    canvas_wrap = tk.Frame(root, bg=PANEL, padx=5, pady=5)
    canvas_wrap.pack(fill="x", padx=22, pady=(1, 4))
    canvas = tk.Canvas(canvas_wrap, width=1038, height=345, bg="#111f30",
                       highlightthickness=0)
    canvas.pack(fill="x")

    def draw_static():
        c = canvas
        c.delete("all")
        # Judul area dan dekorasi garis grid
        c.create_text(18, 15, anchor="nw", text="SIMULASI CONVEYOR — TAMPAK ATAS",
                      fill=MUTED, font=("Segoe UI", 9, "bold"))
        for x in range(20, 1040, 40):
            c.create_line(x, 38, x, 345, fill="#182b40", width=1)
        for y in range(45, 345, 30):
            c.create_line(20, y, 1030, y, fill="#182b40", width=1)

        # Belt conveyor: pendekatan visual, bukan model mekanik riil.
        c.create_rectangle(65, 170, 927, 225, fill="#34465a", outline="#607991", width=2)
        c.create_rectangle(65, 179, 927, 216, fill="#26374a", outline="")
        for x in range(83, 913, 45):
            c.create_line(x, 179, x + 21, 216, fill="#3b5067", width=2)
        c.create_text(83, 235, anchor="w", text="MASUK", fill=MUTED, font=("Segoe UI", 9))
        c.create_text(930, 235, anchor="e", text="ARAH →", fill=MUTED, font=("Segoe UI", 9))
        c.create_line(103, 151, 103, 227, fill=GREEN, width=2, dash=(4, 3))
        c.create_text(103, 142, text="S0", fill=GREEN, font=("Segoe UI", 9, "bold"))
        # Stasiun identifikasi (logam & plastik virtual)
        c.create_line(CLASSIFIER_X, 151, CLASSIFIER_X, 228, fill=ORANGE, width=2, dash=(5, 3))
        c.create_text(CLASSIFIER_X, 143, text="S1 + S2  (KLASIFIKASI)",
                      fill=ORANGE, font=("Segoe UI", 9, "bold"))

        # Saluran ke bin atas/bawah & jalur sisa
        c.create_rectangle(408, 51, 523, 112, fill="#15384f", outline=BLUE, width=2)
        c.create_text(465, 76, text="WADAH LOGAM", fill=TEXT,
                      font=("Segoe UI", 9, "bold"))
        c.create_text(465, 94, text="Counter 1", fill=MUTED, font=("Segoe UI", 9))
        c.create_line(465, 112, 465, 170, fill=BLUE, width=3, dash=(7, 4))
        c.create_text(465, 158, text="P1", fill=BLUE, font=("Segoe UI", 9, "bold"))

        c.create_rectangle(615, 282, 739, 338, fill="#49371e", outline=ORANGE, width=2)
        c.create_text(677, 301, text="WADAH PLASTIK", fill=TEXT,
                      font=("Segoe UI", 9, "bold"))
        c.create_text(677, 321, text="Counter 2", fill=MUTED, font=("Segoe UI", 9))
        c.create_line(677, 225, 677, 282, fill=ORANGE, width=3, dash=(7, 4))
        c.create_text(695, 252, text="P2", fill=ORANGE, font=("Segoe UI", 9, "bold"))

        c.create_rectangle(932, 163, 1030, 232, fill="#334253", outline="#a9b6c7", width=2)
        c.create_text(981, 184, text="LAINNYA", fill=TEXT,
                      font=("Segoe UI", 9, "bold"))
        c.create_text(981, 200, text="(tanpa dorong)", fill=MUTED,
                      font=("Segoe UI", 8))
        c.create_text(981, 215, text="Counter 3", fill=MUTED,
                      font=("Segoe UI", 8))

        c.create_text(22, 332, anchor="w", fill=MUTED, font=("Segoe UI", 9),
                      text="S0: sensor masuk   |   S1: induktif   |   S2: indikator plastik   |   P1/P2: pendorong")

    draw_static()

    # ------------------------------- Sensor -----------------------------
    status_frame = tk.Frame(root, bg=BG)
    status_frame.pack(fill="x", padx=22, pady=(0, 3))
    tk.Label(status_frame, text="SENSOR / AKTUATOR", bg=BG, fg=MUTED,
             font=("Segoe UI", 9, "bold")).pack(anchor="w")
    indicators = tk.Frame(status_frame, bg=BG)
    indicators.pack(fill="x", pady=(3, 0))
    led_labels = {}
    indicator_items = [
        ("entry", "Masuk"), ("metal", "Logam"),
        ("plastic", "Plastik"), ("out_metal", "Count logam"),
        ("out_plastic", "Count plastik"), ("out_other", "Count lainnya"),
        ("servo_metal", "Servo logam"), ("servo_plastic", "Servo plastik"),
    ]
    for key, title in indicator_items:
        lbl = tk.Label(indicators, text="● " + title, bg=PANEL,
                       fg=MUTED, font=("Segoe UI", 9), padx=10, pady=5)
        lbl.pack(side="left", padx=(0, 6))
        led_labels[key] = lbl

    # ------------------------------ Kontrol -----------------------------
    control = tk.Frame(root, bg=PANEL, padx=12, pady=7)
    control.pack(fill="x", padx=22, pady=(2, 5))

    def button(parent, text, command, background, foreground="#07121c"):
        return tk.Button(parent, text=text, command=command, bg=background,
                         fg=foreground, activebackground=background,
                         activeforeground=foreground, relief="flat",
                         padx=12, pady=8, cursor="hand2",
                         font=("Segoe UI", 9, "bold"))

    left = tk.Frame(control, bg=PANEL)
    left.pack(side="left")
    button(left, "▶ MULAI", sim.start, GREEN).pack(side="left", padx=(0, 5))
    button(left, "Ⅱ JEDA", sim.pause, RED).pack(side="left", padx=(0, 5))

    def do_reset():
        if messagebox.askyesno("Reset TRIWISE", "Hapus antrean dan nolkan semua counter?"):
            sim.reset()
            auto_var.set(False)
            sim.auto_mode = False

    button(left, "↺ RESET", do_reset, "#374c63", TEXT).pack(side="left", padx=(0, 10))

    tk.Label(left, text="MASUKKAN:", fg=MUTED, bg=PANEL,
             font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
    button(left, "+ Logam", lambda: sim.add("metal"), BLUE).pack(side="left", padx=(0, 5))
    button(left, "+ Plastik", lambda: sim.add("plastic"), ORANGE).pack(side="left", padx=(0, 5))
    button(left, "+ Lainnya", lambda: sim.add("other"), "#a9b6c7").pack(side="left")

    second = tk.Frame(root, bg=BG)
    second.pack(fill="x", padx=22, pady=(0, 2))
    auto_var = tk.BooleanVar(value=False)

    def on_auto_toggle():
        sim.auto_mode = bool(auto_var.get())
        sim._write_log("Mode otomatis " + ("ON" if sim.auto_mode else "OFF"))

    tk.Checkbutton(second, text="Mode otomatis (benda acak)", variable=auto_var,
                   command=on_auto_toggle, bg=BG, fg=TEXT, selectcolor=PANEL,
                   activebackground=BG, activeforeground=TEXT,
                   font=("Segoe UI", 10)).pack(side="left")

    tk.Label(second, text="Kecepatan conveyor", bg=BG, fg=MUTED,
             font=("Segoe UI", 9)).pack(side="left", padx=(20, 8))
    speed_var = tk.DoubleVar(value=120)

    def on_speed(value):
        sim.speed = float(value)

    tk.Scale(second, from_=50, to=230, orient="horizontal", variable=speed_var,
             command=on_speed, bg=BG, fg=TEXT, troughcolor=GRID,
             activebackground=GREEN, highlightthickness=0,
             length=210, showvalue=True, resolution=10).pack(side="left")
    queue_label = tk.Label(second, text="Antrean: 0", bg=BG, fg=MUTED,
                           font=("Segoe UI", 10, "bold"))
    queue_label.pack(side="right")

    # ------------------------------- Log --------------------------------
    bottom = tk.Frame(root, bg=PANEL, padx=12, pady=8)
    bottom.pack(fill="both", expand=True, padx=22, pady=(1, 10))
    status_text = tk.Label(bottom, text=sim.status, bg=PANEL, fg=TEXT,
                           font=("Segoe UI", 10, "bold"), anchor="w")
    status_text.pack(fill="x", pady=(0, 5))
    log_text = tk.Text(bottom, height=5, wrap="word", bg=PANEL_2, fg=MUTED,
                       insertbackground=TEXT, relief="flat",
                       font=("Consolas", 9), state="disabled")
    log_text.pack(fill="both", expand=True)

    def update_log():
        # Hanya tulis ulang bila riwayat event berubah.
        lines = tuple(sim.events)
        if lines != getattr(update_log, "previous", None):
            log_text.configure(state="normal")
            log_text.delete("1.0", "end")
            log_text.insert("1.0", "\n".join(lines[-8:]))
            log_text.see("end")
            log_text.configure(state="disabled")
            update_log.previous = lines

    last_frame = time.perf_counter()
    belt_shift = 0.0

    def animate():
        nonlocal last_frame, belt_shift
        now = time.perf_counter()
        dt = min(now - last_frame, 0.08)
        last_frame = now
        sim.step(dt)
        if sim.running:
            belt_shift = (belt_shift + sim.speed * dt) % 45.0

        # Canvas gambar statis + objek bergerak + efek servo.
        draw_static()
        if sim.running:
            for x in range(83, 913, 45):
                offset = belt_shift
                # Setiap marka bergeser ke kanan mengikuti arah belt.
                xx = x + offset
                if xx < 910:
                    canvas.create_line(xx, 182, xx + 11, 212,
                                       fill="#7a91aa", width=2)
        if sim.actuator == "metal":
            canvas.create_rectangle(454, 155, 477, 185, fill=RED, outline="")
            canvas.create_text(487, 146, text="P1 AKTIF", fill=RED,
                               font=("Segoe UI", 9, "bold"), anchor="w")
        if sim.actuator == "plastic":
            canvas.create_rectangle(666, 211, 689, 244, fill=RED, outline="")
            canvas.create_text(700, 239, text="P2 AKTIF", fill=RED,
                               font=("Segoe UI", 9, "bold"), anchor="w")
        if sim.active is not None:
            item = sim.active
            color = MATERIAL_COLORS[item.actual]
            canvas.create_oval(item.x - 12, item.y - 12,
                               item.x + 12, item.y + 12,
                               fill=color, outline=TEXT, width=2)
            canvas.create_text(item.x, item.y - 21,
                               text=CATEGORY_NAMES[item.actual],
                               fill=TEXT, font=("Segoe UI", 9, "bold"))

        for key, lbl in counter_labels.items():
            value = sim.total if key == "total" else sim.counts[key]
            lbl.configure(text=str(value))
        state_label.configure(text="● CONVEYOR ON" if sim.running else "● CONVEYOR OFF",
                              fg=GREEN if sim.running else RED)
        status_text.configure(text=sim.status)
        queue_label.configure(text="Antrean: " + str(len(sim.queue)))
        for key, led in led_labels.items():
            active = (sim.actuator == "metal" if key == "servo_metal" else
                      sim.actuator == "plastic" if key == "servo_plastic" else
                      sim.sensor_active(key))
            led.configure(fg=GREEN if active else MUTED,
                          bg="#1f3945" if active else PANEL)
        update_log()
        root.after(30, animate)

    def on_close():
        sim.pause()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    animate()
    root.mainloop()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        launch_gui()
