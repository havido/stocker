import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiGet, apiPost, setToken, TOKEN_KEY } from "@/lib/api";

/**
 * Regression tests for the global 401 handler.
 *
 * Bug: a 401 from the auth endpoints (`/v1/auth/*`) was being hijacked by the
 * global "session expired" handler, which cleared the token and hard-redirected
 * to /login — so an invalid login reloaded the page and cleared the form instead
 * of surfacing the server's "Invalid email or password" message.
 */
describe("api client — 401 handling", () => {
  let locationHref: string;
  const originalLocation = window.location;

  beforeEach(() => {
    localStorage.clear();
    locationHref = "";
    Object.defineProperty(window, "location", {
      configurable: true,
      value: {
        get href() {
          return locationHref;
        },
        set href(v: string) {
          locationHref = v;
        },
      },
    });
  });

  afterEach(() => {
    Object.defineProperty(window, "location", {
      configurable: true,
      value: originalLocation,
    });
    vi.restoreAllMocks();
  });

  it("surfaces the server error detail on a failed login instead of redirecting", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Invalid email or password" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      })
    );

    await expect(
      apiPost("/v1/auth/login", { email: "a@b.com", password: "wrong" })
    ).rejects.toThrow("Invalid email or password");

    // The login page must stay put — no hard redirect.
    expect(locationHref).toBe("");
  });

  it("clears the session and redirects on a 401 from a protected endpoint", async () => {
    setToken("stale-token");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Invalid or expired token" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      })
    );

    await expect(apiGet("/v1/users/watchlist")).rejects.toThrow();

    expect(locationHref).toBe("/login");
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
  });
});
