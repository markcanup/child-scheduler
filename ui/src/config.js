export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:3001";
export const DEFAULT_HUB_ID = import.meta.env.VITE_DEFAULT_HUB_ID || "default-hub";

export const COGNITO_DOMAIN = import.meta.env.VITE_COGNITO_DOMAIN || "";
export const COGNITO_CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID || "";
export const COGNITO_REDIRECT_URI =
  import.meta.env.VITE_COGNITO_REDIRECT_URI || window.location.origin;
export const COGNITO_LOGOUT_URI = import.meta.env.VITE_COGNITO_LOGOUT_URI || window.location.origin;
