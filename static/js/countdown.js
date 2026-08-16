/**
 * countdown.js — Live session timer.
 *
 * Reads:
 *   window.SIGN_IN_MS    — Unix ms timestamp (UTC) of sign-in
 *   window.MAX_SECONDS   — Session limit in seconds (default 10800 = 3h)
 *   window.SESSION_ACTIVE — Boolean; if false the timer does not start
 *
 * The server is authoritative for enforcement; this timer is display-only.
 */
(function () {
  "use strict";

  if (!window.SESSION_ACTIVE) return;

  var timerEl   = document.getElementById("countdown-timer");
  var noticeEl  = document.getElementById("warning-notice");
  var pillEl    = document.getElementById("status-pill");

  if (!timerEl) return;

  var expiresAt = window.SIGN_IN_MS + window.MAX_SECONDS * 1000;
  var intervalId;

  /** Pad a number to 2 digits. */
  function pad(n) { return String(n).padStart(2, "0"); }

  /** Format a non-negative integer of seconds as HH:MM:SS. */
  function formatTime(s) {
    return pad(Math.floor(s / 3600)) + ":" +
           pad(Math.floor((s % 3600) / 60)) + ":" +
           pad(s % 60);
  }

  /** Show (or update) the warning notice bar. */
  function setNotice(text, level) {
    if (!noticeEl) return;
    // level: "warn" | "critical"
    var bg    = level === "critical" ? "var(--c-danger-bg)"  : "var(--c-warn-bg)";
    var color = level === "critical" ? "var(--c-danger)"     : "var(--c-warn)";
    noticeEl.style.background = bg;
    noticeEl.style.color      = color;
    noticeEl.textContent      = text;
    noticeEl.classList.remove("d-none");
  }

  /** Update the session status pill text and class. */
  function setPill(text, cls) {
    if (!pillEl) return;
    pillEl.textContent  = text;
    pillEl.className    = "session-status-pill " + cls;
  }

  function tick() {
    var remaining = Math.max(0, Math.floor((expiresAt - Date.now()) / 1000));

    timerEl.textContent = formatTime(remaining);
    timerEl.className   = "";   // reset state classes

    if (remaining <= 0) {
      timerEl.classList.add("state-expired");
      timerEl.textContent = "00:00:00";
      setNotice("Your session has expired. Please leave the room.", "critical");
      setPill("Session Expired", "critical");
      clearInterval(intervalId);
      // Reload after 5 s so the page reflects the server state.
      setTimeout(function () { window.location.reload(); }, 5000);
      return;
    }

    if (remaining <= 600) {
      // ≤ 10 minutes
      timerEl.classList.add("state-critical");
      setNotice("Less than 10 minutes remaining — please wrap up.", "critical");
      setPill("\u26A0 Ending Soon", "critical");
    } else if (remaining <= 1800) {
      // ≤ 30 minutes
      timerEl.classList.add("state-warn");
      setNotice("30 minutes remaining — your session will end soon.", "warn");
      setPill("Session Ending Soon", "warning");
    }
  }

  tick();
  intervalId = setInterval(tick, 1000);
})();
