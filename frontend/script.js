/**
 * script.js — Attendance page logic
 *
 * Responsibilities:
 *  - Live clock (updates every second)
 *  - Load employees into the dropdown
 *  - Submit attendance and handle all response states
 *  - Show result banner with auto-dismiss timer
 */

'use strict';

// ── DOM references ────────────────────────────────────────────────────────────
const liveTime    = document.getElementById('live-time');
const liveDate    = document.getElementById('live-date');
const select      = document.getElementById('employee-select');
const form        = document.getElementById('attendance-form');
const submitBtn   = document.getElementById('submit-btn');
const banner      = document.getElementById('result-banner');
const detailChips = document.getElementById('detail-chips');
const resetWrap   = document.getElementById('reset-bar-wrap');
const resetFill   = document.getElementById('reset-bar-fill');
const resetLabel  = document.getElementById('reset-label');

let resetTimer = null;

// ── Clock ─────────────────────────────────────────────────────────────────────

function startClock() {
  function tick() {
    const now = new Date();

    // Time: hh:MM:SS AM/PM  (12-hour format)
    liveTime.textContent = now.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    });

    // Date: Thursday, 19 June 2026
    liveDate.textContent = now.toLocaleDateString('en-GB', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  }

  tick();
  setInterval(tick, 1000);
}

// ── Employees ─────────────────────────────────────────────────────────────────

async function loadEmployees() {
  try {
    const res = await fetch('/employees');
    if (!res.ok) throw new Error('Failed to load employees');

    const employees = await res.json();

    if (employees.length === 0) {
      const opt = document.createElement('option');
      opt.disabled = true;
      opt.textContent = 'No employees found';
      select.appendChild(opt);
      return;
    }

    employees.forEach(emp => {
      const opt = document.createElement('option');
      opt.value = emp.id;
      opt.textContent = emp.full_name;
      select.appendChild(opt);
    });
  } catch (err) {
    showBanner('Failed to load employee list. Please refresh the page.', 'error');
  }
}

// Enable submit button only when a valid employee is chosen
select.addEventListener('change', () => {
  submitBtn.disabled = !select.value;
});

// ── Attendance submission ─────────────────────────────────────────────────────

function getLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Browser without Geolocation support.'));
    } else {
      navigator.geolocation.getCurrentPosition(
        position => resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude }),
        error => {
          let msg = "Unable to determine your location.";
          if (error.code === error.PERMISSION_DENIED) {
            msg = "Please enable location services to continue.";
          } else if (error.code === error.TIMEOUT) {
            msg = "GPS timeout.";
          }
          reject(new Error(msg));
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      );
    }
  });
}

async function registerAttendance(employeeId, latitude, longitude) {
  try {
    const res = await fetch('/attendance', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        employee_id: parseInt(employeeId, 10),
        latitude,
        longitude
      }),
    });

    const json = await res.json();
    return json;
  } catch (err) {
    return {
      success: false,
      action: 'error',
      message: 'Network error. Please check your connection and try again.',
      data: null,
    };
  }
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const employeeId = select.value;
  if (!employeeId) return;

  // Loading state
  setLoading(true);
  hideBanner();
  clearChips();
  clearResetBar();

  showBanner("Getting your location...", "warning");

  let location;
  try {
    location = await getLocation();
  } catch (err) {
    setLoading(false);
    showBanner('✕ ' + err.message, "error");
    scheduleReset(8);
    return;
  }

  const result = await registerAttendance(employeeId, location.latitude, location.longitude);

  setLoading(false);

  if (result.action === 'check_in') {
    showBanner('✓ ' + result.message, 'success');
    showChips(result.data, 'check_in');
    scheduleReset(5);

  } else if (result.action === 'check_out') {
    showBanner('✓ ' + result.message, 'success');
    showChips(result.data, 'check_out');
    scheduleReset(5);

  } else if (result.action === 'rejected') {
    showBanner('⚠ ' + result.message, 'warning');
    scheduleReset(8);

  } else {
    showBanner('✕ ' + result.message, 'error');
    scheduleReset(8);
  }
});

// ── UI helpers ────────────────────────────────────────────────────────────────

function setLoading(isLoading) {
  submitBtn.classList.toggle('loading', isLoading);
  submitBtn.disabled = isLoading;
  const icon = submitBtn.querySelector('.btn-icon');
  if (icon) icon.style.display = isLoading ? 'none' : '';
}

function showBanner(message, type) {
  banner.textContent = message;
  banner.className = `result-banner show ${type}`;
}

function hideBanner() {
  banner.className = 'result-banner';
  banner.textContent = '';
}

function showChips(data, action) {
  if (!data) return;

  const chips = [];

  if (action === 'check_in') {
    if (data.late_minutes && data.late_minutes > 0) {
      chips.push({ label: `Late: ${data.late_minutes} min`, cls: 'chip-warning' });
    } else {
      chips.push({ label: 'On Time ✓', cls: 'chip-success' });
    }
  }

  if (action === 'check_out') {
    if (data.working_hours) {
      chips.push({ label: `Worked: ${data.working_hours}h`, cls: '' });
    }
    if (data.missing_minutes && data.missing_minutes > 0) {
      chips.push({ label: `Early Leave: ${data.missing_minutes} min`, cls: 'chip-warning' });
    }
    if (data.overtime_minutes && data.overtime_minutes > 0) {
      chips.push({ label: `Overtime: ${data.overtime_minutes} min`, cls: 'chip-success' });
    }
    if (data.attendance_status) {
      chips.push({ label: data.attendance_status, cls: '' });
    }
  }

  if (chips.length === 0) return;

  detailChips.innerHTML = chips
    .map(c => `<span class="chip ${c.cls}">${c.label}</span>`)
    .join('');

  detailChips.classList.add('show');
}

function clearChips() {
  detailChips.classList.remove('show');
  detailChips.innerHTML = '';
}

// ── Auto-reset ────────────────────────────────────────────────────────────────

/**
 * After `seconds` seconds, reset the form so the next employee can use it.
 */
function scheduleReset(seconds) {
  clearResetBar();
  resetWrap.classList.add('show');

  // Animate the fill bar shrinking from 100% to 0% over `seconds` seconds
  resetFill.style.transition = 'none';
  resetFill.style.width = '100%';

  // Trigger reflow before animating
  void resetFill.offsetWidth;
  resetFill.style.transition = `width ${seconds}s linear`;
  resetFill.style.width = '0%';

  let remaining = seconds;
  resetLabel.textContent = `Resetting in ${remaining}s...`;

  const tick = setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      clearInterval(tick);
      resetForm();
    } else {
      resetLabel.textContent = `Resetting in ${remaining}s...`;
    }
  }, 1000);

  resetTimer = tick;
}

function clearResetBar() {
  if (resetTimer) {
    clearInterval(resetTimer);
    resetTimer = null;
  }
  resetWrap.classList.remove('show');
  resetFill.style.width = '100%';
}

function resetForm() {
  select.value = '';
  submitBtn.disabled = true;
  hideBanner();
  clearChips();
  clearResetBar();
}

// ── Initialise ────────────────────────────────────────────────────────────────

startClock();
loadEmployees();
