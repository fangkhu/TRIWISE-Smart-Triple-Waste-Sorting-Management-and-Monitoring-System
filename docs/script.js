/*
 * TRIWISE LAB — Simulasi Web (HTML/CSS/JavaScript, tanpa perangkat fisik).
 * Port logika dari simulation/main.py (Tkinter).
 * Invariannya: satu benda aktif; prioritas logam -> plastik -> lainnya;
 * counter hanya +1 setelah benda sampai di keluaran; jeda membekukan waktu.
 * Sensor plastik IDEAL hanya untuk simulasi; sensor kapasitif fisik perlu uji.
 * Semua perhitungan ini VIRTUAL, bukan pembacaan ESP32/PLC.
 */
(() => {
  'use strict';
  const CATEGORIES = {
    metal: { label: 'Logam', badge: 'LOGAM', color: '#69caff' },
    plastic: { label: 'Plastik', badge: 'PLASTIK', color: '#ffcc83' },
    other: { label: 'Lainnya', badge: 'LAINNYA', color: '#b7c5d0' }
  };
  const LAYOUT = Object.freeze({
    BELT_Y: 198, ENTRY_X: 104, CLASSIFIER_X: 265,
    METAL_PUSHER_X: 465, PLASTIC_PUSHER_X: 677,
    OTHER_EXIT_X: 908, METAL_EXIT_Y: 110, PLASTIC_EXIT_Y: 282
  });
  const $ = (id) => document.getElementById(id);
  const roundTime = (time) => {
    const minutes = Math.floor(time / 60);
    const seconds = time - minutes * 60;
    return String(minutes).padStart(2, '0') + ':' + seconds.toFixed(1).padStart(4, '0');
  };

  class TriwiseSimulator {
    constructor() {
      this.running = false;
      this.autoMode = false;
      this.speed = 120;
      this.autoInterval = 1;
      this.elapsed = 0;
      this.nextAllowedStart = 0;
      this.lastSpawnAt = -999;
      this.active = null;
      this.queue = [];
      this.counts = { metal: 0, plastic: 0, other: 0 };
      this.lastResult = 'Belum ada benda yang disortir';
      this.status = 'Sistem siap. Tambahkan benda, lalu tekan MULAI.';
      this.events = [];
      this.flashUntil = {};
      this.actuator = null;
      this.log('Simulator siap. Motor dan pendorong OFF.');
    }
    log(message) {
      this.events.push({ time: roundTime(this.elapsed), message, counts: { ...this.counts } });
      if (this.events.length > 80) this.events.shift();
    }
    flash(sensor) { this.flashUntil[sensor] = this.elapsed + 0.65; }
    sensorActive(sensor) { return this.elapsed < (this.flashUntil[sensor] ?? -1); }
    add(category) {
      if (!Object.hasOwn(CATEGORIES, category)) throw new Error('Kategori tidak dikenal');
      this.queue.push(category);
      this.status = `${CATEGORIES[category].label} masuk antrean (${this.queue.length} benda).`;
      this.log(`Antrean masuk: ${CATEGORIES[category].label}`);
    }
    start() {
      if (!this.running) {
        this.running = true;
        this.status = 'Conveyor ON. Menunggu benda atau memproses antrean.';
        this.log('Conveyor ON');
      }
    }
    pause() {
      if (this.running) {
        this.running = false;
        this.status = 'Conveyor OFF / simulasi dijeda.';
        this.log('Conveyor OFF (jeda)');
      }
    }
    reset() {
      this.pause();
      this.elapsed = 0;
      this.active = null;
      this.queue.length = 0;
      this.counts = { metal: 0, plastic: 0, other: 0 };
      this.lastSpawnAt = -999;
      this.nextAllowedStart = 0;
      this.lastResult = 'Belum ada benda yang disortir';
      this.status = 'Semua counter dan antrean telah direset.';
      this.flashUntil = {};
      this.actuator = null;
      this.autoMode = false;
      this.events = [];
      this.log('Reset selesai: semua counter 0; conveyor OFF');
    }
    spawn(category) {
      this.active = {
        actual: category,
        x: LAYOUT.ENTRY_X, y: LAYOUT.BELT_Y,
        classified: false, predicted: null, phase: 'conveyor'
      };
      this.lastSpawnAt = this.elapsed;
      this.flash('entry');
      this.status = `Benda masuk conveyor: ${CATEGORIES[category].label}`;
      this.log('Sensor masuk: benda baru terdeteksi');
    }
    classify(item) {
      // Model IDEAL: bukan klaim bahwa sensor kapasitif dapat mengenali semua plastik.
      const metalDetected = item.actual === 'metal';
      const plasticDetected = item.actual === 'plastic';
      if (metalDetected) this.flash('metal');
      if (plasticDetected) this.flash('plastic');
      // Logam memiliki prioritas seperti di simulation/main.py.
      item.predicted = metalDetected ? 'metal' : plasticDetected ? 'plastic' : 'other';
      item.classified = true;
      this.status = `Hasil klasifikasi: ${CATEGORIES[item.predicted].label}`;
      this.log(`Klasifikasi → ${CATEGORIES[item.predicted].label}`);
    }
    finish(category) {
      this.flash('out_' + category);
      this.counts[category] += 1;
      this.lastResult = `Benda masuk wadah ${CATEGORIES[category].label}`;
      this.status = this.lastResult + '; counter +1';
      this.log(this.status);
      this.active = null;
      this.actuator = null;
      this.nextAllowedStart = this.elapsed + 0.3;
      this.lastFinishedCategory = category;
      this.lastFinishedAt = this.elapsed;
    }
    step(dt) {
      if (!this.running || dt <= 0) return;
      this.elapsed += dt;
      const item = this.active;
      if (!item) {
        if (this.elapsed < this.nextAllowedStart) return;
        if (this.queue.length) this.spawn(this.queue.shift());
        else if (this.autoMode && this.elapsed - this.lastSpawnAt >= this.autoInterval) {
          const types = Object.keys(CATEGORIES);
          this.spawn(types[Math.floor(Math.random() * types.length)]);
        }
        return;
      }
      if (item.phase === 'conveyor') {
        item.x += this.speed * dt;
        if (!item.classified && item.x >= LAYOUT.CLASSIFIER_X) this.classify(item);
        if (item.predicted === 'metal' && item.x >= LAYOUT.METAL_PUSHER_X) {
          item.x = LAYOUT.METAL_PUSHER_X;
          item.phase = 'push_metal';
          this.actuator = 'metal';
          this.status = 'Servo logam AKTIF: mendorong ke wadah logam';
          this.log('Servo pendorong LOGAM ON');
        } else if (item.predicted === 'plastic' && item.x >= LAYOUT.PLASTIC_PUSHER_X) {
          item.x = LAYOUT.PLASTIC_PUSHER_X;
          item.phase = 'push_plastic';
          this.actuator = 'plastic';
          this.status = 'Servo plastik AKTIF: mendorong ke wadah plastik';
          this.log('Servo pendorong PLASTIK ON');
        } else if (item.predicted === 'other' && item.x >= LAYOUT.OTHER_EXIT_X) {
          this.finish('other');
        }
      } else if (item.phase === 'push_metal') {
        item.y -= this.speed * 1.65 * dt;
        if (item.y <= LAYOUT.METAL_EXIT_Y) this.finish('metal');
      } else if (item.phase === 'push_plastic') {
        item.y += this.speed * 1.65 * dt;
        if (item.y >= LAYOUT.PLASTIC_EXIT_Y) this.finish('plastic');
      }
    }
    get total() { return this.counts.metal + this.counts.plastic + this.counts.other; }
  }

  const sim = new TriwiseSimulator();
  const svgNS = 'http://www.w3.org/2000/svg';
  const stripes = $('belt-stripes');
  // Garis bergerak secara virtual; tidak bergantung pada file gambar eksternal.
  for (let x = -80; x < 1040; x += 43) {
    const line = document.createElementNS(svgNS, 'path');
    line.setAttribute('d', `M${x} 180 l21 35`);
    line.setAttribute('stroke', '#527889');
    line.setAttribute('stroke-width', '2.7');
    line.setAttribute('opacity', '0.65');
    stripes.appendChild(line);
  }
  const countEls = {
    metal: $('count-metal'), plastic: $('count-plastic'),
    other: $('count-other'), total: $('count-total')
  };
  const sensorChips = [...document.querySelectorAll('[data-sensor]')];
  let previousCounts = { metal: 0, plastic: 0, other: 0, total: 0 };
  let lastEvent = null;
  let wasMissionDone = false;
  let toastTimeout = null;
  let beltShift = 0;

  function toast(message) {
    const el = $('toast');
    el.textContent = message;
    el.classList.add('visible');
    clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => el.classList.remove('visible'), 2500);
  }
  function add(category) {
    sim.add(category);
    render();
    toast(`${CATEGORIES[category].label} ditambahkan ke antrean`);
  }
  function toggleRunning() {
    if (sim.running) sim.pause(); else sim.start();
    render();
  }
  function reset() {
    sim.reset();
    $('auto-toggle').checked = false;
    wasMissionDone = false;
    previousCounts = { metal: 0, plastic: 0, other: 0, total: 0 };
    lastEvent = null;
    beltShift = 0;
    render();
    toast('Simulasi dimulai ulang ✦');
  }
  function updateLogs() {
    const newest = sim.events[sim.events.length - 1];
    if (newest === lastEvent) return;
    lastEvent = newest;
    const container = $('event-list');
    container.replaceChildren();
    sim.events.slice(-7).reverse().forEach((event) => {
      const li = document.createElement('li');
      const t = document.createElement('span');
      t.className = 'event-time'; t.textContent = event.time;
      const label = document.createElement('span'); label.textContent = event.message;
      li.append(t, label);
      container.appendChild(li);
    });
  }
  function render() {
    const state = sim.running;
    $('runtime-pill').classList.toggle('running', state);
    $('runtime-pill').lastChild.textContent = state ? ' RUNNING' : ' IDLE';
    $('motor-light').classList.toggle('running', state);
    $('motion-dot').classList.toggle('running', state);
    $('motor-label').textContent = state ? 'MOTOR ONLINE' : 'MOTOR OFFLINE';
    $('motor-desc').textContent = state ? 'Conveyor sedang berjalan' : 'Conveyor berhenti';
    $('status-heading').textContent = state ? 'Sistem aktif' : 'Sistem standby';
    $('status-line').textContent = sim.status;
    $('clock').textContent = roundTime(sim.elapsed);
    $('queue-count').textContent = String(sim.queue.length);
    let phase = '';
    if (sim.active) {
      const item = sim.active;
      if (!item.classified) phase = 'entry';
      else if (item.phase === 'conveyor') phase = 'classify';
      else phase = 'push';
    } else if (sim.elapsed - (sim.lastFinishedAt ?? -999) <= 0.7) phase = 'count';
    const phases = ['entry', 'classify', 'push', 'count'];
    document.querySelectorAll('.flow-step').forEach((el) => {
      const index = phases.indexOf(el.dataset.phase);
      const activeIndex = phases.indexOf(phase);
      el.classList.toggle('active', el.dataset.phase === phase);
      el.classList.toggle('done', activeIndex >= 0 && index < activeIndex);
    });
    $('current-phase-label').textContent = phase ? ({entry:'DETECTING',classify:'CLASSIFYING',push:'SORTING',count:'COUNT COMPLETE'})[phase] : 'READY TO SORT';
    for (const key of Object.keys(sim.counts)) {
      const val = sim.counts[key];
      if (val !== previousCounts[key]) {
        countEls[key].parentElement.classList.remove('bump');
        void countEls[key].parentElement.offsetWidth;
        countEls[key].parentElement.classList.add('bump');
        previousCounts[key] = val;
      }
      countEls[key].textContent = String(val);
    }
    countEls.total.textContent = String(sim.total);
    previousCounts.total = sim.total;
    sensorChips.forEach((chip) => {
      const key = chip.dataset.sensor;
      const active = key === 'servo_metal' ? sim.actuator === 'metal' :
        key === 'servo_plastic' ? sim.actuator === 'plastic' : sim.sensorActive(key);
      chip.classList.toggle('active', active);
    });
    $('pusher-metal').setAttribute('fill', sim.actuator === 'metal' ? '#78f8ca' : '#6bb8d8');
    $('pusher-metal').setAttribute('height', sim.actuator === 'metal' ? '33' : '14');
    $('pusher-metal').setAttribute('y', sim.actuator === 'metal' ? '150' : '160');
    $('pusher-plastic').setAttribute('fill', sim.actuator === 'plastic' ? '#78f8ca' : '#d99c67');
    $('pusher-plastic').setAttribute('height', sim.actuator === 'plastic' ? '33' : '14');
    $('entry-glow').setAttribute('visibility', sim.sensorActive('entry') ? 'visible' : 'hidden');
    $('class-glow').setAttribute('visibility', (sim.sensorActive('metal') || sim.sensorActive('plastic')) ? 'visible' : 'hidden');
    stripes.setAttribute('transform', `translate(${beltShift.toFixed(2)} 0)`);
    const obj = $('active-object');
    if (sim.active) {
      const item = sim.active;
      const category = CATEGORIES[item.actual];
      obj.setAttribute('visibility', 'visible');
      obj.setAttribute('transform', `translate(${item.x.toFixed(2)} ${item.y.toFixed(2)})`);
      $('object-shape').setAttribute('fill', category.color);
      $('object-halo').setAttribute('stroke', category.color);
      $('object-shape').setAttribute('rx', item.actual === 'metal' ? '4' : item.actual === 'plastic' ? '10' : '1');
      $('object-caption').textContent = category.badge;
    } else obj.setAttribute('visibility', 'hidden');
    updateLogs();
    const progress = Math.min(100, sim.total / 5 * 100);
    $('mission-progress').style.width = progress + '%';
    $('mission-text').textContent = Math.min(sim.total, 5) + ' / 5';
    $('mission-copy').textContent = sim.total >= 5
      ? 'Misi selesai! ✦ Hebat, semua material berhasil diproses.'
      : `Sortir ${5 - sim.total} benda lagi untuk menyelesaikan misi pertama!`;
    if (sim.total >= 5 && !wasMissionDone) {
      wasMissionDone = true;
      toast('✦ Misi selesai! 5 benda berhasil disortir.');
    }
  }

  // Interaksi dengan kontrol HTML.
  $('btn-start').addEventListener('click', () => { sim.start(); render(); });
  $('btn-pause').addEventListener('click', () => { sim.pause(); render(); });
  document.querySelectorAll('[data-add]').forEach((btn) => {
    btn.addEventListener('click', () => add(btn.dataset.add));
  });
  $('btn-batch').addEventListener('click', () => {
    ['metal', 'plastic', 'other', 'plastic', 'metal', 'other'].forEach((c) => sim.add(c));
    render(); toast('✦ Batch demo: 6 benda masuk antrean');
  });
  $('auto-toggle').addEventListener('change', (ev) => {
    sim.autoMode = ev.target.checked;
    sim.log('Mode otomatis ' + (sim.autoMode ? 'ON' : 'OFF'));
    render(); toast(sim.autoMode ? 'Mode otomatis aktif' : 'Mode otomatis nonaktif');
  });
  $('speed-range').addEventListener('input', (ev) => {
    sim.speed = Number(ev.target.value);
    $('speed-val').textContent = String(sim.speed);
  });
  const resetDialog = $('reset-dialog');
  $('btn-reset').addEventListener('click', () => {
    if (typeof resetDialog.showModal === 'function') resetDialog.showModal();
    else if (window.confirm('Reset semua counter dan antrean TRIWISE?')) reset();
  });
  $('btn-cancel-reset').addEventListener('click', () => resetDialog.close());
  $('btn-confirm-reset').addEventListener('click', () => { resetDialog.close(); reset(); });
  document.addEventListener('keydown', (event) => {
    const el = event.target;
    if (el instanceof HTMLElement && (['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(el.tagName) || el.isContentEditable)) return;
    if (resetDialog.open || event.altKey || event.ctrlKey || event.metaKey || event.repeat) return;
    const keyMap = { '1': 'metal', '2': 'plastic', '3': 'other' };
    if (keyMap[event.key]) add(keyMap[event.key]);
    else if (event.code === 'Space') { event.preventDefault(); toggleRunning(); }
  });
  $('btn-csv').addEventListener('click', () => {
    const escapeCell = (v) => '"' + String(v).replaceAll('"', '""') + '"';
    const rows = [['waktu', 'aktivitas', 'jumlah_logam', 'jumlah_plastik', 'jumlah_lainnya']];
    sim.events.forEach((e) => rows.push([e.time, e.message, e.counts.metal, e.counts.plastic, e.counts.other]));
    const csv = '\ufeff' + rows.map((cols) => cols.map(escapeCell).join(';')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'triwise-log-simulasi.csv';
    document.body.appendChild(link);
    link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast('Riwayat CSV berhasil diekspor');
  });

  // requestAnimationFrame + dt capped = sejalan dengan Tkinter main.py asli.
  let lastFrame = performance.now();
  function frame(now) {
    const dt = Math.min((now - lastFrame) / 1000, 0.08);
    lastFrame = now;
    sim.step(dt);
    if (sim.running) beltShift = (beltShift + sim.speed * dt) % 43;
    render();
    requestAnimationFrame(frame);
  }
  render();
  requestAnimationFrame(frame);
  // Read-only-ish diagnostic handle for browser test; never controls hardware.
  Object.defineProperty(window, 'TRIWISE_SIM', { value: sim, writable: false });
})();
