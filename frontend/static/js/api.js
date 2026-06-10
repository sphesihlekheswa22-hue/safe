/* SafeRoute AI - API client.
 * Thin wrapper around fetch that attaches the JWT and centralizes error
 * handling. The token lives in localStorage; there is no client-side role
 * trust - the server enforces everything.
 */
const SR = (() => {
  const TOKEN_KEY = "sr_token";
  const USER_KEY = "sr_user";

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }
  function setSession(token, user) {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
  function getUser() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || "null");
    } catch (e) {
      return null;
    }
  }
  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  async function request(path, { method = "GET", body, auth = true } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (auth) {
      const t = getToken();
      if (t) headers["Authorization"] = "Bearer " + t;
    }

    let res;
    try {
      res = await fetch(path, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch (e) {
      const err = new Error("Network error — check your connection and try again.");
      err.status = 0;
      err.cause = e;
      throw err;
    }

    let data = null;
    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      try {
        data = await res.json();
      } catch (e) {
        data = null;
      }
    }

    if (res.status === 401 && auth) {
      clearSession();
      if (!location.pathname.startsWith("/login") && location.pathname !== "/" && location.pathname !== "/register") {
        location.href = "/login";
      }
    }

    if (!res.ok) {
      const message = (data && (data.error || data.msg)) || `Request failed (${res.status})`;
      const err = new Error(message);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  return {
    getToken, setSession, getUser, clearSession,
    get: (p) => request(p),
    post: (p, body, opts = {}) => request(p, { method: "POST", body, ...opts }),
    put: (p, body) => request(p, { method: "PUT", body }),
    del: (p) => request(p, { method: "DELETE" }),
    // auth-free helpers for login/register
    login: (body) => request("/api/auth/login", { method: "POST", body, auth: false }),
    register: (body) => request("/api/auth/register", { method: "POST", body, auth: false }),
  };
})();
