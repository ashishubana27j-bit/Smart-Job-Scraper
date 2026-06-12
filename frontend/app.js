const API = "";

// Tabs
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    if (btn.dataset.tab === "files") loadFiles();
    if (btn.dataset.tab === "schedule") loadSchedules();
  });
});

const GROUP_LABELS = {
  remote_api: "Remote (API)",
  aggregators: "Aggregators",
  uae_gulf: "UAE / Gulf",
  ats_careers: "ATS Career Pages",
  difficult: "Hard to scrape (may block)",
};

// Load portals
async function loadPortals() {
  const res = await fetch(`${API}/api/portals`);
  const data = await res.json();
  const container = document.getElementById("portal-checkboxes");
  const defaultOn = new Set([
    "remotive", "remoteok", "arbeitnow", "workingnomads", "weworkremotely",
    "jobspresso", "greenhouse", "lever", "indeed" , "linkedin",
  ]);

  let html = "";
  if (data.groups) {
    for (const [key, portals] of Object.entries(data.groups)) {
      html += `<div class="portal-group"><strong>${GROUP_LABELS[key] || key}</strong><div class="checkbox-grid">`;
      html += portals
        .map(
          (p) =>
            `<label class="checkbox"><input type="checkbox" name="portal" value="${p}" ${defaultOn.has(p) ? "checked" : ""} /> ${p}</label>`
        )
        .join("");
      html += `</div></div>`;
    }
  } else {
    html = data.portals
      .map(
        (p) =>
          `<label class="checkbox"><input type="checkbox" name="portal" value="${p}" ${defaultOn.has(p) ? "checked" : ""} /> ${p}</label>`
      )
      .join("");
  }
  container.innerHTML = html;
}
loadPortals();

// Scrape form
document.getElementById("scrape-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const btn = document.getElementById("scrape-btn");
  btn.disabled = true;

  const portals = [...form.querySelectorAll('input[name="portal"]:checked')].map((el) => el.value);
  const formats = [];
  if (form.fmt_excel.checked) formats.push("excel");
  if (form.fmt_json.checked) formats.push("json");
  if (form.fmt_csv.checked) formats.push("csv");

  const body = {
    skills: form.skills.value,
    location: form.location.value,
    remote_only: form.remote_only.checked,
    max_results: parseInt(form.max_results.value, 10),
    portals,
    output_formats: formats.length ? formats : ["excel"],
  };

  document.getElementById("scrape-status").classList.remove("hidden");
  document.getElementById("jobs-table-wrap").classList.add("hidden");
  document.getElementById("status-text").textContent = "Starting scrape...";
  document.getElementById("status-fill").className = "";
  document.getElementById("portal-summary").innerHTML = "";
  document.getElementById("saved-files").innerHTML = "";

  try {
    const res = await fetch(`${API}/api/scrape`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const { task_id } = await res.json();
    pollStatus(task_id);
  } catch (err) {
    document.getElementById("status-text").textContent = `Error: ${err.message}`;
    document.getElementById("status-fill").className = "failed";
    btn.disabled = false;
  }
});

async function pollStatus(taskId) {
  const fill = document.getElementById("status-fill");
  const text = document.getElementById("status-text");
  const btn = document.getElementById("scrape-btn");

  const poll = async () => {
    const res = await fetch(`${API}/api/scrape/status/${taskId}`);
    const data = await res.json();

    text.textContent = data.progress || data.status;

    if (data.status === "running" || data.status === "pending") {
      fill.style.width = "60%";
      setTimeout(poll, 2000);
      return;
    }

    if (data.status === "completed") {
      fill.className = "done";
      text.textContent = `Done — ${data.job_count} jobs in ${data.elapsed_seconds}s`;
      renderPortalSummary(data.portal_summary);
      renderSavedFiles(data.saved_files);
      renderJobs(data.jobs, data.job_count);
      btn.disabled = false;
      return;
    }

    fill.className = "failed";
    text.textContent = data.error || "Scrape failed";
    btn.disabled = false;
  };

  poll();
}

function renderPortalSummary(summary) {
  const el = document.getElementById("portal-summary");
  if (!summary?.length) return;
  el.innerHTML = summary
    .map(
      (p) =>
        `<div class="portal-row">
          <span>${p.portal}</span>
          <span class="${p.success ? "ok" : "err"}">${p.success ? `${p.total_found} jobs (${p.duration_seconds}s)` : p.error || "failed"}</span>
        </div>`
    )
    .join("");
}

function renderSavedFiles(files) {
  const el = document.getElementById("saved-files");
  if (!files?.length) return;
  el.innerHTML = files
    .map((f) => `<a href="${API}/api/files/download/${f}" download>${f}</a>`)
    .join("");
}

function renderJobs(jobs, total) {
  const wrap = document.getElementById("jobs-table-wrap");
  const tbody = document.querySelector("#jobs-table tbody");
  document.getElementById("job-count").textContent = `(${total})`;
  wrap.classList.remove("hidden");

  tbody.innerHTML = jobs
    .map(
      (j) => `
    <tr>
      <td>${Math.round((j.skill_match_score || 0) * 100)}%</td>
      <td>${esc(j.title)}</td>
      <td>${esc(j.company)}</td>
      <td>${esc(j.location)}</td>
      <td>${esc(j.source_portal)}</td>
      <td>${formatDate(j.scraped_at)}</td>
      <td><a href="${esc(j.url)}" target="_blank" rel="noopener">Open</a></td>
    </tr>`
    )
    .join("");
}

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s || "";
  return d.innerHTML;
}

function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString();
}

function formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

// Files
async function loadFiles() {
  const res = await fetch(`${API}/api/files`);
  const files = await res.json();
  const el = document.getElementById("files-list");

  if (!files.length) {
    el.innerHTML = '<p class="empty">No exported files yet. Run a scrape first.</p>';
    return;
  }

  el.innerHTML = files
    .map(
      (f) => `
    <div class="file-item">
      <div>
        <span class="badge ${f.format}">${f.format}</span>
        <strong>${esc(f.filename)}</strong>
        <div class="file-meta">${formatDate(f.created_at)} · ${formatBytes(f.size_bytes)}</div>
      </div>
      <div class="file-actions">
        <a class="btn" href="${API}/api/files/download/${f.filename}" download>Download</a>
      </div>
    </div>`
    )
    .join("");
}

document.getElementById("refresh-files").addEventListener("click", loadFiles);

// Schedule
document.getElementById("schedule-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const body = {
    name: form.name.value,
    skills: form.skills.value,
    location: form.location.value,
    run_time: form.run_time.value,
  };

  const res = await fetch(`${API}/api/schedule`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (res.ok) {
    form.skills.value = "";
    loadSchedules();
  } else {
    const err = await res.json();
    alert(err.detail || "Failed to create schedule");
  }
});

async function loadSchedules() {
  const res = await fetch(`${API}/api/schedule`);
  const schedules = await res.json();
  const el = document.getElementById("schedules-list");

  if (!schedules.length) {
    el.innerHTML = '<p class="empty">No schedules yet. Add one above to scrape automatically every day.</p>';
    return;
  }

  el.innerHTML = schedules
    .map(
      (s) => `
    <div class="schedule-item">
      <div>
        <strong>${esc(s.name)}</strong> — ${esc(s.skills)}
        <div class="schedule-meta">
          Daily at ${s.run_time} · ${esc(s.location)}
          ${s.next_run ? `· Next: ${formatDate(s.next_run)}` : ""}
          ${s.last_run ? `· Last: ${formatDate(s.last_run)} (${s.last_job_count || 0} jobs)` : ""}
        </div>
        ${s.last_file ? `<div class="file-links"><a href="${API}/api/files/download/${s.last_file}" download>${esc(s.last_file)}</a></div>` : ""}
      </div>
      <div class="schedule-actions">
        <button class="btn" onclick="toggleSchedule('${s.id}', ${!s.enabled})">${s.enabled ? "Pause" : "Enable"}</button>
        <button class="btn danger" onclick="deleteSchedule('${s.id}')">Delete</button>
      </div>
    </div>`
    )
    .join("");
}

async function deleteSchedule(id) {
  if (!confirm("Delete this schedule?")) return;
  await fetch(`${API}/api/schedule/${id}`, { method: "DELETE" });
  loadSchedules();
}

async function toggleSchedule(id, enabled) {
  await fetch(`${API}/api/schedule/${id}/toggle?enabled=${enabled}`, { method: "PATCH" });
  loadSchedules();
}
