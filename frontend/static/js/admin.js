// System Admin Control Center — drives the 7 admin panels.

(function () {

  "use strict";

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  const $ = (id) => document.getElementById(id);

  const fmtRole = (r) => String(r || "").replaceAll("_", " ");



  let roles = [];

  const loaded = {};



  // ---------- Tabs ----------

  document.querySelectorAll(".admin-tab").forEach((tab) =>

    tab.addEventListener("click", () => {

      document.querySelectorAll(".admin-tab").forEach((t) => t.classList.remove("active"));

      tab.classList.add("active");

      const name = tab.dataset.tab;

      document.querySelectorAll(".admin-panel").forEach((p) => p.classList.add("hidden"));

      $("panel-" + name).classList.remove("hidden");

      lazyLoad(name);

    })

  );



  function lazyLoad(name) {

    const map = {

      users: loadUsers, ai: loadAI,

      system: loadSystem, audit: loadAudit, security: loadSecurity,

    };

    if (map[name] && !loaded[name]) { map[name](); loaded[name] = true; }

  }



  // ---------- Modal helpers ----------

  function openModal(boxId) {

    $("modal-backdrop").classList.remove("hidden");

    document.querySelectorAll("#modal-backdrop .modal-box").forEach((b) => b.classList.add("hidden"));

    $(boxId).classList.remove("hidden");

  }

  function closeModal() { $("modal-backdrop").classList.add("hidden"); }

  document.querySelectorAll(".modal-close").forEach((b) => b.addEventListener("click", closeModal));

  $("modal-backdrop").addEventListener("click", (e) => { if (e.target.id === "modal-backdrop") closeModal(); });



  // ========================================================= USERS

  async function loadUsers() {

    try {

      const [{ users }, { roles: r }] = await Promise.all([

        SR.get("/api/admin/users"), SR.get("/api/admin/roles"),

      ]);

      roles = r;

      $("users-body").innerHTML = users.length ? users.map((u) => `

        <tr>

          <td>

            <div class="font-semibold text-surface-800">${esc(u.name)}</div>

            <div class="text-xs text-surface-500">${esc(u.email)}</div>

          </td>

          <td><span class="badge badge-blue">${esc(fmtRole(u.role))}</span></td>

          <td>${u.is_active ? '<span class="badge badge-low">Active</span>' : '<span class="badge badge-high">Blocked</span>'}</td>

          <td class="text-right whitespace-nowrap">

            <button class="btn-ghost" data-edit='${JSON.stringify(u).replace(/'/g, "&#39;")}'>Edit</button>

            <button class="btn-ghost" data-pw="${u.id}" data-email="${esc(u.email)}">Reset PW</button>

            <button class="btn-ghost" data-toggle="${u.id}" data-active="${u.is_active}">${u.is_active ? "Block" : "Unblock"}</button>

            <button class="btn-danger" data-del="${u.id}">Delete</button>

          </td>

        </tr>`).join("") : '<tr><td colspan="4" class="text-surface-400 py-6 text-center">No users.</td></tr>';

      wireUserButtons();

    } catch (e) { flash(e.message, "error"); }

  }



  function wireUserButtons() {

    const body = $("users-body");

    body.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", () => openUserModal(JSON.parse(b.dataset.edit))));

    body.querySelectorAll("[data-pw]").forEach((b) => b.addEventListener("click", () => openPwModal(b.dataset.pw, b.dataset.email)));

    body.querySelectorAll("[data-toggle]").forEach((b) => b.addEventListener("click", async () => {

      try { await SR.put(`/api/admin/users/${b.dataset.toggle}/status`, { is_active: b.dataset.active !== "true" }); flash("Status updated.", "success"); loadUsers(); }

      catch (e) { flash(e.message, "error"); }

    }));

    body.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", async () => {

      if (!confirm("Permanently delete this user?")) return;

      try { await SR.del("/api/admin/users/" + b.dataset.del); flash("User deleted.", "success"); loadUsers(); }

      catch (e) { flash(e.message, "error"); }

    }));

  }



  function fillRoleSelect() {

    $("user-role-select").innerHTML = roles.map((r) => `<option value="${r}">${fmtRole(r)}</option>`).join("");

  }



  function openUserModal(user) {

    fillRoleSelect();

    const f = $("user-form");

    const isEdit = !!user;

    $("user-modal-title").textContent = isEdit ? "Edit User" : "New User";

    f.id.value = isEdit ? user.id : "";

    f.name.value = isEdit ? user.name : "";

    f.email.value = isEdit ? user.email : "";

    f.role.value = isEdit ? user.role : "PUBLIC_USER";

    // On edit, name/email become read-only (role is the editable bit here)

    f.name.readOnly = isEdit; f.email.readOnly = isEdit;

    $("user-pw-wrap").classList.toggle("hidden", isEdit);

    f.password.required = !isEdit;

    openModal("user-modal");

  }



  $("btn-create-user").addEventListener("click", () => openUserModal(null));



  $("user-form").addEventListener("submit", async (e) => {

    e.preventDefault();

    const f = e.target;

    const id = f.id.value;

    try {

      if (id) {

        await SR.put(`/api/admin/users/${id}/role`, { role: f.role.value });

        flash("User updated.", "success");

      } else {

        await SR.post("/api/admin/users", {

          name: f.name.value, email: f.email.value, password: f.password.value,

          role: f.role.value,

        });

        flash("User created.", "success");

      }

      closeModal(); loadUsers();

    } catch (err) { flash(err.message, "error"); }

  });



  function openPwModal(id, email) {

    const f = $("pw-form"); f.id.value = id; f.password.value = "";

    $("pw-modal-user").textContent = email;

    openModal("pw-modal");

  }

  $("pw-form").addEventListener("submit", async (e) => {

    e.preventDefault();

    const f = e.target;

    try { await SR.put(`/api/admin/users/${f.id.value}/password`, { password: f.password.value }); flash("Password reset.", "success"); closeModal(); }

    catch (err) { flash(err.message, "error"); }

  });



  // ========================================================= AI MODEL

  let aiSettings = {};

  function setToggle(el, on) { el.dataset.on = on ? "true" : "false"; }



  async function loadAI() {

    try {

      const { settings } = await SR.get("/api/admin/settings");

      aiSettings = settings;

      setToggle($("toggle-risk"), settings.risk_engine_enabled);

      $("sentiment-mode").value = settings.sentiment_mode;

      document.querySelectorAll(".model-option").forEach((m) => m.classList.toggle("active", m.dataset.model === settings.ai_model));

      setWeight("w-sev", settings.weight_severity);

      setWeight("w-den", settings.weight_density);

      setWeight("w-sen", settings.weight_sentiment);

      loadModelInfo();

    } catch (e) { flash(e.message, "error"); }

  }



  async function loadModelInfo() {

    try {

      const info = await SR.get("/api/reports/model-info");

      $("model-info").textContent = JSON.stringify(info, null, 2);

    } catch (e) { $("model-info").textContent = "Model info unavailable: " + e.message; }

  }



  function setWeight(id, val) { $(id).value = val; $(id + "-val").textContent = Number(val).toFixed(2); }

  ["w-sev", "w-den", "w-sen"].forEach((id) =>

    $(id).addEventListener("input", () => { $(id + "-val").textContent = Number($(id).value).toFixed(2); }));



  $("toggle-risk").addEventListener("click", () => setToggle($("toggle-risk"), $("toggle-risk").dataset.on !== "true"));

  document.querySelectorAll(".model-option").forEach((m) => m.addEventListener("click", () => {

    document.querySelectorAll(".model-option").forEach((x) => x.classList.remove("active"));

    m.classList.add("active");

  }));



  $("save-ai").addEventListener("click", async () => {

    const model = document.querySelector(".model-option.active");

    try {

      await SR.put("/api/admin/settings", {

        risk_engine_enabled: $("toggle-risk").dataset.on === "true",

        sentiment_mode: $("sentiment-mode").value,

        ai_model: model ? model.dataset.model : "rule_based",

      });

      flash("AI configuration saved.", "success");

    } catch (e) { flash(e.message, "error"); }

  });



  $("save-weights").addEventListener("click", async () => {

    try {

      await SR.put("/api/admin/settings", {

        weight_severity: parseFloat($("w-sev").value),

        weight_density: parseFloat($("w-den").value),

        weight_sentiment: parseFloat($("w-sen").value),

      });

      flash("Risk weights applied.", "success");

    } catch (e) { flash(e.message, "error"); }

  });



  $("recompute-btn").addEventListener("click", async () => {

    try { await SR.post("/api/ai/recompute", {}); flash("Risk areas recomputed.", "success"); loadModelInfo(); }

    catch (e) { flash(e.message, "error"); }

  });



  // ========================================================= SYSTEM MONITORING

  async function loadSystem() {

    try {

      const s = await SR.get("/api/admin/system");

      chip("svc-api", s.services.api === "ok");

      chip("svc-db", s.services.database === "up");

      chip("svc-risk", s.services.risk_engine === "enabled", s.services.risk_engine);

      $("sys-logins").textContent = s.recent_logins_24h;

      const labels = { users: "Users", active_users: "Active", events: "Events", routes: "Routes", risk_areas: "Risk Areas" };

      $("system-counts").innerHTML = Object.entries(s.counts).map(([k, v]) =>

        `<div class="stat-tile"><div class="text-2xl font-display font-bold text-primary-600">${v}</div><div class="text-xs text-surface-500 mt-1">${labels[k] || k}</div></div>`).join("");

      $("server-time").textContent = "Server time: " + new Date(s.server_time).toLocaleString();

      const pill = $("system-pill");

      pill.classList.toggle("bg-emerald-50", s.status === "operational");

      pill.querySelector("span:last-child").textContent = s.status === "operational" ? "System Operational" : "System Degraded";

    } catch (e) { flash(e.message, "error"); }

  }

  function chip(id, ok, label) {

    const el = $(id);

    el.className = "status-chip " + (ok ? "ok" : "bad");

    el.textContent = label || (ok ? "OK" : "DOWN");

  }

  $("refresh-system").addEventListener("click", loadSystem);



  // ========================================================= AUDIT

  async function loadAudit(action) {

    try {

      const q = action ? "?action=" + encodeURIComponent(action) : "";

      const { audit } = await SR.get("/api/admin/audit" + q);

      $("audit-body").innerHTML = audit.length ? audit.map((a) => `

        <tr>

          <td class="text-surface-500 whitespace-nowrap">${new Date(a.created_at).toLocaleString()}</td>

          <td>${esc(a.actor_email || "system")}</td>

          <td><span class="badge badge-blue">${esc(a.action)}</span></td>

          <td>${esc(a.target || "—")}</td>

          <td class="text-surface-500">${esc(a.detail || "")}</td>

        </tr>`).join("") : '<tr><td colspan="5" class="text-surface-400 py-6 text-center">No audit entries.</td></tr>';

    } catch (e) { flash(e.message, "error"); }

  }

  let auditTimer;

  $("audit-filter").addEventListener("input", (e) => {

    clearTimeout(auditTimer);

    auditTimer = setTimeout(() => loadAudit(e.target.value.trim()), 300);

  });



  // ========================================================= SECURITY

  async function loadSecurity() {

    try {

      const { settings, permission_matrix } = await SR.get("/api/admin/settings");

      setToggle($("toggle-registration"), settings.registration_open);

      $("rl-max").value = settings.rate_limit_max;

      $("rl-window").value = settings.rate_limit_window;

      $("jwt-exp").value = settings.jwt_expiry_minutes;

      $("perm-matrix").innerHTML = Object.entries(permission_matrix).map(([cap, rs]) => `

        <div class="p-3 rounded-lg bg-surface-50 border border-surface-200">

          <div class="font-mono text-xs font-semibold text-surface-800 mb-1">${esc(cap)}</div>

          <div class="flex flex-wrap gap-1">${rs.map((r) => `<span class="badge badge-gray text-[10px]">${fmtRole(r)}</span>`).join("")}</div>

        </div>`).join("");

    } catch (e) { flash(e.message, "error"); }

  }

  $("toggle-registration").addEventListener("click", () => setToggle($("toggle-registration"), $("toggle-registration").dataset.on !== "true"));

  $("save-security").addEventListener("click", async () => {

    try {

      await SR.put("/api/admin/settings", {

        registration_open: $("toggle-registration").dataset.on === "true",

        rate_limit_max: parseInt($("rl-max").value, 10),

        rate_limit_window: parseInt($("rl-window").value, 10),

        jwt_expiry_minutes: parseInt($("jwt-exp").value, 10),

      });

      flash("Security settings saved.", "success");

    } catch (e) { flash(e.message, "error"); }

  });



  // ========================================================= BROADCAST

  $("broadcast-form").addEventListener("submit", async (e) => {

    e.preventDefault();

    if (!confirm("Send this emergency broadcast to the selected audience?")) return;

    try {

      const res = await SR.post("/api/admin/broadcast", {

        message: $("bc-message").value, severity: $("bc-severity").value, target_role: $("bc-target").value,

      });

      flash(`Broadcast sent to ${res.recipients} user(s).`, "success");

      $("broadcast-form").reset();

    } catch (err) { flash(err.message, "error"); }

  });



  // ---------- Init ----------

  document.addEventListener("sr:user-ready", () => {

    loadUsers(); loaded.users = true;

  });

})();

