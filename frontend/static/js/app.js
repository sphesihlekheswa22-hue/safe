/* SafeRoute AI - Premium Application Shell */
(function () {
  const path = location.pathname;
  const PUBLIC_PAGES = ["/", "/login"];

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
        'SYSTEM_ANALYST': 'text-violet-600',
        'GOVERNMENT_AUTHORITY': 'text-blue-600',
        'TRANSPORT_OPERATOR': 'text-emerald-600',
        'INSTITUTION_ADMIN': 'text-indigo-600',
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
    if (breadcrumb && user.institution) {
      breadcrumb.textContent = `${user.institution.name} / ${document.getElementById('page-heading')?.textContent || 'Dashboard'}`;
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

    } catch (e) {
      // 401 handled in api.js
      console.error('Failed to load user:', e);
    }
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
