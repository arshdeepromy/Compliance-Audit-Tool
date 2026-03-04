/**
 * Tōtika Audit Tool — Auto-save and UI interactions.
 *
 * Provides debounced auto-save for the criterion scoring form.
 * On any form input change, waits 2 seconds after the last input,
 * then PUTs the form data as JSON to /api/audits/<id>/score.
 */

(function () {
  "use strict";

  // -----------------------------------------------------------------------
  // Sidebar toggle (mobile)
  // -----------------------------------------------------------------------

  function initSidebarToggle() {
    var toggleBtn = document.getElementById("sidebar-toggle");
    var sidebar = document.getElementById("app-sidebar");
    var overlay = document.getElementById("sidebar-overlay");

    if (!toggleBtn || !sidebar) return;

    function openSidebar() {
      sidebar.classList.add("open");
      if (overlay) overlay.classList.add("active");
      toggleBtn.setAttribute("aria-expanded", "true");
    }

    function closeSidebar() {
      sidebar.classList.remove("open");
      if (overlay) overlay.classList.remove("active");
      toggleBtn.setAttribute("aria-expanded", "false");
    }

    toggleBtn.addEventListener("click", function () {
      if (sidebar.classList.contains("open")) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });

    if (overlay) {
      overlay.addEventListener("click", closeSidebar);
    }

    // Close sidebar on Escape key
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && sidebar.classList.contains("open")) {
        closeSidebar();
      }
    });
  }

  // -----------------------------------------------------------------------
  // Score dot update on auto-save
  // -----------------------------------------------------------------------

  /**
   * Update the sidebar score dot for a criterion after a successful save.
   * Called from doSave on successful response.
   */
  function updateSidebarDot(criterionCode, score, isNa) {
    var sidebarItem = document.querySelector(
      '.sidebar-item[data-criterion="' + criterionCode + '"]'
    );
    if (!sidebarItem) return;

    var dot = sidebarItem.querySelector(".score-dot");
    if (!dot) return;

    // Remove all colour classes
    dot.className = "score-dot";

    if (isNa) {
      dot.classList.add("na");
      dot.title = "N/A";
    } else if (score === null || score === undefined) {
      dot.classList.add("grey");
      dot.title = "Unscored";
    } else if (score >= 3) {
      dot.classList.add("green");
      dot.title = "Score: " + score;
    } else if (score === 2) {
      dot.classList.add("amber");
      dot.title = "Score: " + score;
    } else {
      dot.classList.add("red");
      dot.title = "Score: " + score;
    }
  }

  // -----------------------------------------------------------------------
  // Auto-save for the scoring form
  // -----------------------------------------------------------------------

  var DEBOUNCE_MS = 2000;
  var saveTimer = null;
  var statusEl = null;

  /**
   * Collect all form data from #score-form and return a JSON-ready object.
   */
  function collectFormData(form) {
    var scoreRadios = form.querySelectorAll('input[name="score"]');
    var selectedScore = null;
    var isNa = false;

    for (var i = 0; i < scoreRadios.length; i++) {
      if (scoreRadios[i].checked) {
        if (scoreRadios[i].value === "na") {
          isNa = true;
        } else {
          selectedScore = parseInt(scoreRadios[i].value, 10);
        }
        break;
      }
    }

    var naReasonEl = form.querySelector('textarea[name="na_reason"]');
    var naReason = naReasonEl ? naReasonEl.value : "";

    var notesEl = form.querySelector('textarea[name="notes"]');
    var notes = notesEl ? notesEl.value : "";

    // Evidence checks — collect all checkboxes whose name starts with "evidence_"
    var evidenceChecks = {};
    var checkboxes = form.querySelectorAll('input[type="checkbox"]');
    for (var j = 0; j < checkboxes.length; j++) {
      var cb = checkboxes[j];
      var match = cb.name.match(/^evidence_(\d+)$/);
      if (match) {
        evidenceChecks[match[1]] = cb.checked;
      }
    }

    return {
      criterion_code: form.getAttribute("data-criterion-code"),
      score: isNa ? null : selectedScore,
      is_na: isNa,
      na_reason: naReason,
      notes: notes,
      evidence_checks: evidenceChecks,
    };
  }

  /**
   * Show a status message in the save-status indicator.
   */
  function setStatus(text, className) {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.className = "save-status " + (className || "");
  }

  /**
   * Send the form data to the auto-save API endpoint.
   */
  function doSave(form) {
    var auditId = form.getAttribute("data-audit-id");
    var url = "/api/audits/" + auditId + "/score";
    var payload = collectFormData(form);

    setStatus("Saving\u2026", "saving");

    var xhr = new XMLHttpRequest();
    xhr.open("PUT", url, true);
    xhr.setRequestHeader("Content-Type", "application/json");

    xhr.onload = function () {
      if (xhr.status >= 200 && xhr.status < 300) {
        setStatus("Saved", "saved");
        // Update sidebar dot colour after successful save
        updateSidebarDot(payload.criterion_code, payload.score, payload.is_na);
      } else {
        var errMsg = "Error";
        try {
          var resp = JSON.parse(xhr.responseText);
          errMsg = resp.error || errMsg;
        } catch (e) {
          // ignore parse errors
        }
        setStatus(errMsg, "error");
      }
    };

    xhr.onerror = function () {
      setStatus("Network error", "error");
    };

    xhr.send(JSON.stringify(payload));
  }

  /**
   * Schedule a debounced save — resets the timer on each call.
   */
  function scheduleSave(form) {
    if (saveTimer) {
      clearTimeout(saveTimer);
    }
    setStatus("Unsaved changes\u2026", "pending");
    saveTimer = setTimeout(function () {
      doSave(form);
    }, DEBOUNCE_MS);
  }

  /**
   * Toggle visibility of the N/A reason field based on score selection.
   */
  function handleNaToggle(form) {
    var naField = document.getElementById("na-reason-field");
    if (!naField) return;

    var naRadio = form.querySelector('input[name="score"][value="na"]');
    if (naRadio && naRadio.checked) {
      naField.style.display = "";
    } else {
      naField.style.display = "none";
    }
  }

  /**
   * Initialise auto-save on the scoring form.
   */
  function initAutoSave() {
    var form = document.getElementById("score-form");
    if (!form) return;

    statusEl = document.getElementById("save-status");

    // Listen for changes on all form inputs
    form.addEventListener("input", function () {
      handleNaToggle(form);
      scheduleSave(form);
    });

    form.addEventListener("change", function () {
      handleNaToggle(form);
      scheduleSave(form);
    });

    // Expose immediate save for the Save button
    var saveBtn = document.getElementById("save-btn");
    if (saveBtn) {
      saveBtn.addEventListener("click", function (e) {
        e.preventDefault();
        if (saveTimer) clearTimeout(saveTimer);
        doSave(form);
      });
    }
  }

  // -----------------------------------------------------------------------
  // Compliance Trend Chart (Chart.js)
  // -----------------------------------------------------------------------

  /**
   * Initialise the compliance trend line chart on the audit detail/dashboard page.
   * Expects a global `complianceTrendData` array of {audit_date, overall_score}.
   */
  function initComplianceTrendChart() {
    var canvas = document.getElementById("complianceTrendChart");
    if (!canvas) return;

    var data = window.complianceTrendData;
    if (!data || !data.length) return;

    var labels = [];
    var scores = [];
    for (var i = 0; i < data.length; i++) {
      labels.push(data[i].audit_date || "");
      scores.push(data[i].overall_score);
    }

    new Chart(canvas, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Overall Score",
            data: scores,
            borderColor: "#f97316",
            backgroundColor: "rgba(249, 115, 22, 0.1)",
            borderWidth: 2,
            pointBackgroundColor: "#f97316",
            pointBorderColor: "#f97316",
            pointRadius: 4,
            pointHoverRadius: 6,
            fill: true,
            tension: 0.3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            labels: {
              color: "#9ca3af",
              font: { family: "'Barlow', sans-serif", size: 12 },
            },
          },
          tooltip: {
            backgroundColor: "#16213e",
            titleColor: "#fb923c",
            bodyColor: "#e0e0e0",
            borderColor: "#2a2a4a",
            borderWidth: 1,
          },
        },
        scales: {
          x: {
            ticks: {
              color: "#9ca3af",
              font: { family: "'Barlow', sans-serif", size: 11 },
            },
            grid: { color: "rgba(42, 42, 74, 0.4)" },
          },
          y: {
            min: 0,
            max: 4,
            ticks: {
              color: "#9ca3af",
              font: { family: "'Barlow', sans-serif", size: 11 },
              stepSize: 1,
            },
            grid: { color: "rgba(42, 42, 74, 0.4)" },
          },
        },
      },
    });
  }

  // -----------------------------------------------------------------------
  // Initialise all components when DOM is ready
  // -----------------------------------------------------------------------

  function initAll() {
    initSidebarToggle();
    initAutoSave();
    initComplianceTrendChart();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }
})();
