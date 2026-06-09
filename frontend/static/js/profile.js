(function () {
  "use strict";

  function fillProfile(user) {
    document.getElementById("profile-name").value = user.name || "";
    document.getElementById("profile-email").value = user.email || "";
    document.getElementById("profile-role").value = (user.role || "").replaceAll("_", " ");
  }

  async function loadStats() {
    try {
      const data = await SR.get("/api/dashboard/summary");
      document.getElementById("profile-routes").textContent = data.kpis.total_routes ?? 0;
      document.getElementById("profile-alerts").textContent = data.kpis.active_alerts ?? 0;
    } catch (e) {
      /* optional stats */
    }
  }

  document.getElementById("profile-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("profile-name").value.trim();
    try {
      const { user } = await SR.put("/api/auth/profile", { name });
      SR.setSession(null, user);
      fillProfile(user);
      flash("Profile updated.", "success");
      document.dispatchEvent(new CustomEvent("sr:user-ready", { detail: user }));
    } catch (err) {
      flash(err.message, "error");
    }
  });

  document.getElementById("password-form").addEventListener("submit", async (e) => {
    e.preventDefault();
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
    }
  });

  document.addEventListener("sr:user-ready", (ev) => {
    fillProfile(ev.detail);
    loadStats();
  });
})();
