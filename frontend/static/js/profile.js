(function () {
  "use strict";

  function initials(name) {
    const parts = (name || "").trim().split(/\s+/).filter(Boolean);
    if (!parts.length) return "?";
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }

  function formatRole(role) {
    return (role || "").replaceAll("_", " ");
  }

  function setBtnLoading(btn, loading, idleHtml) {
    if (!btn) return;
    btn.disabled = loading;
    btn.innerHTML = loading
      ? '<span class="spinner"></span> Saving…'
      : idleHtml;
  }

  function fillProfile(user) {
    const name = user.name || "";
    const email = user.email || "";
    const role = formatRole(user.role);

    document.getElementById("profile-name").value = name;
    document.getElementById("profile-email").value = email;
    document.getElementById("profile-role").value = role;

    const avatar = document.getElementById("profile-avatar");
    const displayName = document.getElementById("profile-display-name");
    const displayEmail = document.getElementById("profile-display-email");
    const roleBadge = document.getElementById("profile-role-badge");

    if (avatar) avatar.textContent = initials(name);
    if (displayName) displayName.textContent = name || "—";
    if (displayEmail) displayEmail.textContent = email || "—";
    if (roleBadge) roleBadge.textContent = role || "—";
  }

  async function loadStats() {
    const routesEl = document.getElementById("profile-routes");
    const eventsEl = document.getElementById("profile-events");
    try {
      const data = await SR.get("/api/dashboard/summary");
      if (routesEl) routesEl.textContent = data.kpis.total_routes ?? 0;
      if (eventsEl) eventsEl.textContent = data.kpis.total_events ?? 0;
    } catch (_) {
      if (routesEl) routesEl.textContent = "—";
      if (eventsEl) eventsEl.textContent = "—";
    }
  }

  document.getElementById("profile-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("profile-save-btn");
    const idleHtml = '<i class="fas fa-check mr-1.5"></i> Save profile';
    setBtnLoading(btn, true, idleHtml);
    const name = document.getElementById("profile-name").value.trim();
    try {
      const { user } = await SR.put("/api/auth/profile", { name });
      SR.setSession(null, user);
      fillProfile(user);
      flash("Profile updated.", "success");
      document.dispatchEvent(new CustomEvent("sr:user-ready", { detail: user }));
    } catch (err) {
      flash(err.message, "error");
    } finally {
      setBtnLoading(btn, false, idleHtml);
    }
  });

  document.getElementById("password-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("password-save-btn");
    const idleHtml = '<i class="fas fa-shield-halved mr-1.5"></i> Update password';
    setBtnLoading(btn, true, idleHtml);
    const fd = new FormData(e.target);
    try {
      await SR.put("/api/auth/password", {
        current_password: fd.get("current_password"),
        new_password: fd.get("new_password"),
      });
      e.target.reset();
      flash("Password updated.", "success");
    } catch (err) {
      flash(err.message, "error");
    } finally {
      setBtnLoading(btn, false, idleHtml);
    }
  });

  document.addEventListener("sr:user-ready", (ev) => {
    fillProfile(ev.detail);
    loadStats();
  });
})();
