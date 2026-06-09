/**
 * Decode a JWT payload (base64url) WITHOUT verifying the signature.
 *
 * Used only to read display claims (sub, email) from a Supabase token we already
 * trust because it arrived via the auth callback. The backend re-validates the
 * token on every authenticated request, so this is never a security boundary.
 */
export function decodeJwt(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const b64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const json = decodeURIComponent(
      atob(b64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(json);
  } catch {
    return null;
  }
}
