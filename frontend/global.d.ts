interface Window {
  __APP_MODE__?: "saas" | "oss";
  __GITHUB_CLIENT_ID__?: string | null;
}

// Allow importing PNG assets (e.g., branding logo)
declare module "*.png" {
  const src: string;
  export default src;
}
