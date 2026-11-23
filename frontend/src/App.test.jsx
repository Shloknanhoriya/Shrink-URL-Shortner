import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.jsx";

const okLink = {
  code: "abc123",
  short_url: "http://localhost:8000/abc123",
  original_url: "https://example.com/long",
  clicks: 0,
  created_at: "2026-01-01T00:00:00+00:00",
};

function mockFetch(status, body) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: status < 400,
    status,
    json: async () => body,
  });
}

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe("App", () => {
  it("shortens a URL and shows it in the list", async () => {
    mockFetch(201, okLink);
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/long url/i), "https://example.com/long");
    await user.click(screen.getByRole("button", { name: /shorten/i }));

    expect(await screen.findByText(okLink.short_url)).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/links",
      expect.objectContaining({ method: "POST" })
    );
    const sent = JSON.parse(globalThis.fetch.mock.calls[0][1].body);
    expect(sent).toEqual({ url: "https://example.com/long" });
  });

  it("sends the custom alias when provided", async () => {
    mockFetch(201, { ...okLink, code: "mine" });
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/long url/i), "https://example.com");
    await user.type(screen.getByLabelText(/custom alias/i), "mine");
    await user.click(screen.getByRole("button", { name: /shorten/i }));

    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalled());
    expect(JSON.parse(globalThis.fetch.mock.calls[0][1].body).alias).toBe("mine");
  });

  it("shows the server error message", async () => {
    mockFetch(409, { detail: "That alias is already taken" });
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/long url/i), "https://example.com");
    await user.click(screen.getByRole("button", { name: /shorten/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("already taken");
  });

  it("validates empty input without calling the API", async () => {
    globalThis.fetch = vi.fn();
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /shorten/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/enter a url/i);
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("shows a friendly message when the backend is unreachable", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/long url/i), "https://example.com");
    await user.click(screen.getByRole("button", { name: /shorten/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/cannot reach the server/i);
  });

  it("restores saved links from localStorage", () => {
    localStorage.setItem("shrink.links", JSON.stringify([okLink]));
    render(<App />);
    expect(screen.getByText(okLink.short_url)).toBeInTheDocument();
  });
});
