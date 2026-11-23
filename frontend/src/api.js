// Thin API client. Relative URLs work in dev (Vite proxy) and in production
// (FastAPI serves the built frontend from the same origin).

function errorMessage(detail) {
  if (typeof detail === "string") return detail;
  // FastAPI validation errors come back as a list of objects
  if (Array.isArray(detail) && detail.length) {
    return detail.map((d) => d.msg || "Invalid input").join(", ");
  }
  return "Something went wrong";
}

export async function createLink(url, alias) {
  const body = { url };
  if (alias && alias.trim()) body.alias = alias.trim();

  let res;
  try {
    res = await fetch("/api/links", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error("Cannot reach the server. Is the backend running?");
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(errorMessage(data.detail));
  return data;
}

export async function getLink(code) {
  const res = await fetch(`/api/links/${encodeURIComponent(code)}`);
  if (!res.ok) throw new Error("Link not found");
  return res.json();
}
