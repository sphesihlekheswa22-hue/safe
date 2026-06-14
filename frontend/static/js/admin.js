// System Admin Control Center — drives the admin panels.

(function () {

  "use strict";

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  const $ = (id) => document.getElementById(id);

  const fmtRole = (r) => String(r || "").replaceAll("_", " ");



  let roles = [];
  let usersById = {};

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

      users: loadUsers,

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
      usersById = Object.fromEntries(users.map((u) => [String(u.id), u]));

      $("users-body").innerHTML = users.length ? users.map((u) => `

        <tr>

          <td>

            <div class="font-semibold text-surface-800">${esc(u.name)}</div>

            <div class="text-xs text-surface-500">${esc(u.email)}</div>

          </td>

          <td><span class="badge badge-blue">${esc(fmtRole(u.role))}</span></td>

          <td>${u.is_active ? '<span class="badge badge-low">Active</span>' : '<span class="badge badge-high">Blocked</span>'}</td>

          <td class="text-right whitespace-nowrap">

            <button class="btn-ghost" data-edit-id="${u.id}">Edit</button>

            <button class="btn-ghost" data-pw="${u.id}" data-email="${esc(u.email)}">Reset PW</button>

            <button class="btn-ghost" data-toggle="${u.id}" data-active="${u.is_active ? "true" : "false"}">${u.is_active ? "Block" : "Unblock"}</button>

            <button class="btn-danger" data-del="${u.id}">Delete</button>

          </td>

        </tr>`).join("") : '<tr><td colspan="4" class="text-surface-400 py-6 text-center">No users.</td></tr>';

      wireUserButtons();

    } catch (e) { flash(e.message, "error"); }

  }



  function wireUserButtons() {

    const body = $("users-body");

    body.querySelectorAll("[data-edit-id]").forEach((b) => b.addEventListener("click", () => {
      const user = usersById[b.dataset.editId];
      if (user) openUserModal(user);
    }));
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

    f.elements.user_id.value = isEdit ? String(user.id) : "";

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

    const userId = f.elements.user_id.value;

    try {

      if (userId) {

        await SR.put(`/api/admin/users/${userId}/role`, { role: f.role.value });

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

    const f = $("pw-form");
    f.elements.user_id.value = String(id);
    f.password.value = "";

    $("pw-modal-user").textContent = email;

    openModal("pw-modal");

  }

  $("pw-form").addEventListener("submit", async (e) => {

    e.preventDefault();

    const f = e.target;

    const userId = f.elements.user_id.value;

    try { await SR.put(`/api/admin/users/${userId}/password`, { password: f.password.value }); flash("Password reset.", "success"); closeModal(); }

    catch (err) { flash(err.message, "error"); }

  });



  function setToggle(el, on) { el.dataset.on = on ? "true" : "false"; }



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

      flash("Emergency broadcast created.", "success");

      $("broadcast-form").reset();

    } catch (err) { flash(err.message, "error"); }

  });



  // ---------- Init ----------

  document.addEventListener("sr:user-ready", () => {

    loadUsers(); loaded.users = true;

  });

})();

