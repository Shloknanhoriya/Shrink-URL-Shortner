import { useEffect, useState } from "react";
import { createLink, getLink } from "./api.js";

const STORAGE_KEY = "shrink.links";

function loadLinks() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export default function App() {
  const [url, setUrl] = useState("");
  const [alias, setAlias] = useState("");
  const [links, setLinks] = useState(loadLinks);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState("");

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(links.slice(0, 20)));
    } catch {
      /* storage unavailable, history just won't persist */
    }
  }, [links]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!url.trim()) {
      setError("Please enter a URL");
      return;
    }
    setLoading(true);
    try {
      const link = await createLink(url.trim(), alias);
      setLinks((prev) => [link, ...prev]);
      setUrl("");
      setAlias("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function copy(link) {
    try {
      await navigator.clipboard.writeText(link.short_url);
      setCopied(link.code);
      setTimeout(() => setCopied(""), 1500);
    } catch {
      setError("Could not copy. Select the link and copy it manually.");
    }
  }

  async function refresh(code) {
    try {
      const fresh = await getLink(code);
      setLinks((prev) => prev.map((l) => (l.code === code ? fresh : l)));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <main className="container">
      <header>
        <h1>🔗 Shrink</h1>
        <p className="tagline">Paste a long URL, get a short one.</p>
      </header>

      <form onSubmit={handleSubmit} className="card" noValidate>
        <label htmlFor="url">Long URL</label>
        <input
          id="url"
          type="text"
          placeholder="https://example.com/some/very/long/path"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          autoFocus
        />

        <label htmlFor="alias">
          Custom alias <span className="optional">(optional)</span>
        </label>
        <input
          id="alias"
          type="text"
          placeholder="my-link"
          value={alias}
          onChange={(e) => setAlias(e.target.value)}
        />

        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}

        <button type="submit" disabled={loading}>
          {loading ? "Shortening…" : "Shorten"}
        </button>
      </form>

      {links.length > 0 && (
        <section className="card" aria-label="Your links">
          <div className="list-header">
            <h2>Your links</h2>
            <button className="link-btn" onClick={() => setLinks([])}>
              Clear
            </button>
          </div>
          <ul>
            {links.map((link) => (
              <li key={link.code}>
                <div className="link-main">
                  <a href={link.short_url} target="_blank" rel="noreferrer">
                    {link.short_url}
                  </a>
                  <span className="original" title={link.original_url}>
                    {link.original_url}
                  </span>
                </div>
                <div className="link-actions">
                  <button
                    className="link-btn"
                    onClick={() => refresh(link.code)}
                    title="Refresh click count"
                  >
                    {link.clicks} {link.clicks === 1 ? "click" : "clicks"} ↻
                  </button>
                  <button className="small" onClick={() => copy(link)}>
                    {copied === link.code ? "Copied!" : "Copy"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
