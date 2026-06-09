import { describe, it, expect } from "vitest";
import { decodeJwt } from "@/lib/jwt";

function makeToken(payload: object): string {
  const b64 = btoa(JSON.stringify(payload))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  return `eyJhbGciOiJIUzI1NiJ9.${b64}.sig`;
}

describe("decodeJwt", () => {
  it("extracts sub and email from a Supabase-style token", () => {
    const token = makeToken({ sub: "658f0e2a-1033-434c", email: "havido0611@gmail.com" });
    const claims = decodeJwt(token);
    expect(claims?.sub).toBe("658f0e2a-1033-434c");
    expect(claims?.email).toBe("havido0611@gmail.com");
  });

  it("returns null for a non-JWT string", () => {
    expect(decodeJwt("not-a-jwt")).toBeNull();
  });

  it("returns null for an empty payload segment", () => {
    expect(decodeJwt("header..sig")).toBeNull();
  });
});
