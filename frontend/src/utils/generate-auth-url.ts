/**
 * Generates a URL to redirect to for OAuth authentication
 * @param identityProvider The identity provider to use (e.g., "github")
 * @param requestUrl The URL of the request
 * @returns The URL to redirect to for OAuth
 */
export const generateAuthUrl = (
  identityProvider: string,
  requestUrl: URL,
  authUrl?: string,
) => {
  // Use HTTPS protocol unless the host is localhost
  const protocol =
    requestUrl.hostname === "localhost" ? requestUrl.protocol : "https:";
  const redirectUri = `${protocol}//${requestUrl.host}/oauth/keycloak/callback`;

  let finalAuthUrl: string;

  if (authUrl) {
    // Ensure https:// is prepended and remove any accidental duplicate slashes
    finalAuthUrl = `https://${authUrl.replace(/^https?:\/\//, "")}`;
  } else {
    finalAuthUrl = requestUrl.hostname
      .replace(/(^|\.)staging\.forge\.dev$/, "$1auth.staging.forge.dev")
      .replace(/(^|\.)app\.forge\.dev$/, "auth.app.forge.dev")
      .replace(/(^|\.)localhost$/, "auth.staging.forge.dev");

    // If no replacements matched, prepend "auth." (excluding localhost)
    if (
      finalAuthUrl === requestUrl.hostname &&
      requestUrl.hostname !== "localhost"
    ) {
      finalAuthUrl = `auth.${requestUrl.hostname}`;
    }

    finalAuthUrl = `https://${finalAuthUrl}`;
  }

  const scope = "openid email profile"; // OAuth scope - not user-facing
  const separator = requestUrl.search ? "&" : "?";
  const cleanHref = requestUrl.href.replace(/\/$/, "");
  const state = `${cleanHref}${separator}login_method=${identityProvider}`;
  return `${finalAuthUrl}/realms/forge/protocol/openid-connect/auth?client_id=forge&kc_idp_hint=${identityProvider}&response_type=code&redirect_uri=${encodeURIComponent(redirectUri)}&scope=${encodeURIComponent(scope)}&state=${encodeURIComponent(state)}`;
};
