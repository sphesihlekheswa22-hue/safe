/* SafeRoute AI - Premium Application Shell */
(function () {
  const path = location.pathname;
  const PUBLIC_PAGES = ["/", "/login", "/register"];

  // Global error surfacing — avoids silent failures during demos
  window.addEventListener("unhandledrejection", (ev) => {
    console.error("Unhandled promise rejection:", ev.reason);
    const msg = ev.reason && ev.reason.message ? ev.reason.message : "Something went wrong.";
    if (!PUBLIC_PAGES.includes(path) && window.showFlash) {
      showFlash(msg, "error");
    }
  });

  window.addEventListener("error", (ev) => {
    console.error("Uncaught error:", ev.error || ev.message);
  });

  // Premium Flash Notification System
  window.showFlash = function(message, type = 'info', duration = 4000) {
    const container = document.getElementById('flash-container');
    if (!container) return;

    const icons = {
      success: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
      error: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
      warning: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>',
      info: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>'
    };

    const colors = {
      success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
      error: 'bg-rose-50 border-rose-200 text-rose-800',
      warning: 'bg-amber-50 border-amber-200 text-amber-800',
      info: 'bg-primary-50 border-primary-200 text-primary-800'
    };

    const el = document.createElement('div');
    el.className = `flash-enter flex items-start gap-3 p-4 rounded-xl border shadow-lg backdrop-blur-sm ${colors[type]}`;
    el.innerHTML = `
      <div class="flex-shrink-0 mt-0.5">${icons[type]}</div>
      <div class="flex-1 text-sm font-medium">${message}</div>
      <button class="flex-shrink-0 opacity-60 hover:opacity-100 transition-opacity" onclick="this.parentElement.remove()">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
      </button>
    `;

    container.appendChild(el);

    // Auto remove
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateX(100%)';
      el.style.transition = 'all 0.3s ease';
      setTimeout(() => el.remove(), 300);
    }, duration);
  };

  // Backwards-compatible alias used by events/alerts/routes/admin pages.
  window.flash = function (message, type = 'info', duration = 4000) {
    window.showFlash(message, type, duration);
  };

  // Apply role-based visibility
  function applyRoleVisibility(role) {
    document.querySelectorAll('[data-roles]').forEach((el) => {
      const allowed = el.getAttribute('data-roles').split(',').map((s) => s.trim());
      if (!allowed.includes(role)) {
        el.style.display = 'none';
      }
    });
  }

  // Mark active navigation
  function markActiveNav() {
    document.querySelectorAll('.nav-link').forEach((link) => {
      const href = link.getAttribute('href');
      if (href === path || path.startsWith(href + '/')) {
        link.classList.add('active');
        link.classList.remove('text-surface-300');
        link.classList.add('bg-white/10', 'text-white', 'border-l-2', 'border-primary-500');
      }
    });
  }

  // Render user in sidebar
  function renderUser(user) {
    const nameEl = document.getElementById('user-name');
    const roleEl = document.getElementById('user-role');
    const avatarEl = document.getElementById('user-avatar');
    const navAvatar = document.getElementById('nav-avatar');

    if (nameEl) {
      nameEl.textContent = user.name || 'User';
      nameEl.classList.remove('animate-pulse');
    }

    if (roleEl) {
      const roleColors = {
        'SYSTEM_ADMIN': 'text-amber-600',
        'PUBLIC_USER': 'text-surface-500'
      };
      roleEl.textContent = (user.role || 'USER').replace(/_/g, ' ');
      roleEl.className = `text-[10px] uppercase tracking-wide font-medium truncate ${roleColors[user.role] || 'text-surface-500'}`;
    }

    const avatar = (user.name || user.email || '?').charAt(0).toUpperCase();
    if (avatarEl) {
      avatarEl.textContent = avatar;
      avatarEl.onclick = () => { location.href = '/profile'; };
    }
    if (navAvatar) {
      navAvatar.textContent = avatar;
      navAvatar.parentElement.onclick = () => { location.href = '/profile'; };
    }

    // Update breadcrumb if element exists
    const breadcrumb = document.getElementById('breadcrumb');
    if (breadcrumb) {
      breadcrumb.textContent = document.getElementById('page-heading')?.textContent || 'Dashboard';
    }
  }

  // Wire logout button
  function wireLogout() {
    const btn = document.getElementById('logout-btn');
    if (!btn) return;

    btn.addEventListener('click', async () => {
      btn.classList.add('opacity-75', 'scale-95');
      try {
        await SR.post('/api/auth/logout');
      } catch (e) {
        // Ignore
      }
      SR.clearSession();
      window.showFlash('Signed out successfully', 'success');
      setTimeout(() => {
        location.href = '/login';
      }, 500);
    });
  }

  function escHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',
    }[c]));
  }

  function severityPill(sev) {
    const styles = {
      CRITICAL: 'bg-gradient-to-r from-rose-600 to-red-700 text-white',
      HIGH: 'bg-gradient-to-r from-orange-500 to-red-500 text-white',
      MEDIUM: 'bg-gradient-to-r from-amber-400 to-orange-500 text-white',
      LOW: 'bg-surface-100 text-surface-600',
    };
    return `<span class="inline-flex px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wide ${styles[sev] || styles.LOW}">${escHtml(sev)}</span>`;
  }

  function sevBadge(sev) {
    const n = Number(sev) || 1;
    const cls = n >= 4 ? 'bg-gradient-to-r from-rose-600 to-red-700 text-white'
      : n >= 3 ? 'bg-gradient-to-r from-orange-500 to-red-500 text-white'
      : 'bg-surface-100 text-surface-600';
    return `<span class="inline-flex px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wide ${cls}">${n}/5</span>`;
  }

  function updateEventBadges(events) {
    const navBadge = document.getElementById('nav-event-badge');
    const countPill = document.getElementById('nav-event-count');
    const urgent = events.filter((e) => Number(e.severity) >= 4).length;
    const total = events.length;

    if (navBadge) {
      if (urgent > 0) {
        navBadge.textContent = urgent > 9 ? '9+' : String(urgent);
        navBadge.classList.remove('hidden');
      } else if (total > 0) {
        navBadge.textContent = total > 9 ? '9+' : String(total);
        navBadge.classList.remove('hidden');
      } else {
        navBadge.classList.add('hidden');
      }
    }

    if (countPill) {
      countPill.textContent = `${total} recent`;
      countPill.classList.toggle('hidden', total === 0);
    }
  }

  function renderEventPanel(events) {
    const list = document.getElementById('nav-event-list');
    if (!list) return;

    if (!events.length) {
      list.innerHTML = `
        <div class="text-center py-8">
          <div class="w-12 h-12 mx-auto mb-2 rounded-full bg-emerald-50 flex items-center justify-center text-xl">✓</div>
          <p class="text-xs text-surface-500">No recent incidents</p>
        </div>`;
      return;
    }

    list.innerHTML = events.slice(0, 8).map((ev) => {
      const border = Number(ev.severity) >= 4 ? 'border-l-rose-500'
        : Number(ev.severity) >= 3 ? 'border-l-orange-500'
        : 'border-l-amber-400';
      const when = ev.created_at
        ? new Date(ev.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
        : '';
      return `
        <div class="rounded-xl border border-surface-100 bg-white p-3 border-l-4 ${border} hover:shadow-sm transition-shadow">
          <p class="text-sm text-surface-700 font-medium leading-snug line-clamp-2">${escHtml(ev.title)}</p>
          <p class="text-[11px] text-surface-500 mt-1">${escHtml(ev.location || '')}</p>
          <div class="flex items-center justify-between gap-2 mt-2">
            ${sevBadge(ev.severity)}
            <span class="text-[10px] text-surface-400 whitespace-nowrap">${escHtml(when)}</span>
          </div>
        </div>`;
    }).join('');
  }

  let navEventsCache = [];

  async function loadNavEvents() {
    try {
      const { events } = await SR.get('/api/events');
      navEventsCache = events || [];
      updateEventBadges(navEventsCache);
      renderEventPanel(navEventsCache);
      return navEventsCache;
    } catch (e) {
      const list = document.getElementById('nav-event-list');
      if (list) {
        list.innerHTML = '<p class="text-xs text-rose-500 text-center py-6">Could not load incidents</p>';
      }
      return [];
    }
  }

  function wireEventBell() {
    const btn = document.getElementById('nav-event-btn');
    const panel = document.getElementById('nav-event-panel');
    const wrap = document.getElementById('nav-event-wrap');
    if (!btn || !panel) return;

    let open = false;

    function setOpen(next) {
      open = next;
      panel.classList.toggle('hidden', !open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      btn.classList.toggle('bg-surface-200', open);
      btn.classList.toggle('text-primary-600', open);
      if (open) loadNavEvents();
    }

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      setOpen(!open);
    });

    document.addEventListener('click', (e) => {
      if (open && wrap && !wrap.contains(e.target)) setOpen(false);
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && open) setOpen(false);
    });
  }

  // Wire mobile menu
  function wireMobileMenu() {
    const btn = document.getElementById('mobile-menu');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const closeBtn = document.getElementById('close-sidebar');

    function openSidebar() {
      sidebar.classList.remove('-translate-x-full');
      overlay.classList.remove('hidden');
      setTimeout(() => overlay.classList.remove('opacity-0'), 10);
    }

    function closeSidebar() {
      sidebar.classList.add('-translate-x-full');
      overlay.classList.add('opacity-0');
      setTimeout(() => overlay.classList.add('hidden'), 300);
    }

    if (btn) btn.addEventListener('click', openSidebar);
    if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
    if (overlay) overlay.addEventListener('click', closeSidebar);
  }

  // Initialize
  async function init() {
    if (PUBLIC_PAGES.includes(path)) return;

    if (!SR.getToken()) {
      location.href = '/login';
      return;
    }

    wireLogout();
    wireMobileMenu();
    wireEventBell();
    markActiveNav();

    // Use cached user for instant paint
    const cached = SR.getUser();
    if (cached) {
      renderUser(cached);
      applyRoleVisibility(cached.role);
    }

    // Fetch fresh user data
    try {
      const { user } = await SR.get('/api/auth/me');
      SR.setSession(null, user);
      renderUser(user);
      applyRoleVisibility(user.role);
      window.SR_USER = user;

      // Dispatch event for page-specific handlers
      document.dispatchEvent(new CustomEvent('sr:user-ready', { detail: user }));

      loadNavEvents();
      setInterval(loadNavEvents, 60000);

    } catch (e) {
      // 401 handled in api.js
      console.error('Failed to load user:', e);
    }
  }

  document.addEventListener('sr:events-updated', (ev) => {
    navEventsCache = ev.detail || [];
    updateEventBadges(navEventsCache);
    const panel = document.getElementById('nav-event-panel');
    if (panel && !panel.classList.contains('hidden')) {
      renderEventPanel(navEventsCache);
    }
  });

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
