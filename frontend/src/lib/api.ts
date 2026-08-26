function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp("(^|;\\s*)" + name + "=([^;]*)"));
  return match ? decodeURIComponent(match[2]) : null;
}

async function request(path: string, options: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  const method = (options.method || "GET").toUpperCase();
  if (method !== "GET") {
    const token = getCookie("csrftoken");
    if (token) headers["X-CSRFToken"] = token;
  }
  return fetch(path, { credentials: "same-origin", ...options, headers });
}

/** Ensure the CSRF cookie exists before the first mutating call. */
export async function ensureCsrf(): Promise<void> {
  if (!getCookie("csrftoken")) await fetch("/api/csrf", { credentials: "same-origin" });
}

export async function api<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  if ((options.method || "GET").toUpperCase() !== "GET") await ensureCsrf();
  const res = await request(`/api${path}`, options);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

/** Multipart upload (photos) — browser sets the Content-Type boundary itself. */
export async function apiUpload<T = unknown>(path: string, file: globalThis.File): Promise<T> {
  await ensureCsrf();
  const token = getCookie("csrftoken");
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`/api${path}`, {
    method: "POST",
    credentials: "same-origin",
    headers: token ? { "X-CSRFToken": token } : {},
    body: form,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

/** allauth headless endpoints return meaningful bodies on non-2xx too. */
export async function allauth(
  method: string,
  path: string,
  body?: unknown,
): Promise<{ status: number; data: any }> {
  await ensureCsrf();
  const res = await request(`/_allauth/browser/v1${path}`, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let data = null;
  try {
    data = await res.json();
  } catch {}
  return { status: res.status, data };
}
