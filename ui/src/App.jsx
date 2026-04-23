import { useEffect, useState } from "react";
import {
  API_BASE_URL,
  COGNITO_CLIENT_ID,
  COGNITO_DOMAIN,
  COGNITO_REDIRECT_URI,
} from "./config";
import CatalogDebugPanel from "./components/CatalogDebugPanel";
import LoginPlaceholder from "./components/LoginPlaceholder";
import ProfilePreferencesPanel from "./components/ProfilePreferencesPanel";
import ScheduleConfigPanel from "./components/ScheduleConfigPanel";

const TOKEN_STORAGE_KEY = "childScheduler.uiAuthToken";
const TOKEN_SESSION_STORAGE_KEY = "childScheduler.uiAuthSession";
const PKCE_VERIFIER_STORAGE_KEY = "childScheduler.pkceVerifier";
const EXCHANGED_CODES_STORAGE_KEY = "childScheduler.exchangedOAuthCodes";
let inFlightCodeExchange = null;
let inFlightCodeValue = "";

function trimTrailingSlash(url) {
  return url.endsWith("/") ? url.slice(0, -1) : url;
}

function tokensFromHash() {
  const hash = window.location.hash || "";
  if (!hash.startsWith("#")) {
    return null;
  }
  const params = new URLSearchParams(hash.slice(1));
  const idToken = params.get("id_token") || "";
  const accessToken = params.get("access_token") || "";
  if (!idToken && !accessToken) {
    return null;
  }
  return { idToken, accessToken };
}

function parseCodeFromSearch() {
  const params = new URLSearchParams(window.location.search);
  return params.get("code") || "";
}

function loadExchangedCodes() {
  try {
    const raw = sessionStorage.getItem(EXCHANGED_CODES_STORAGE_KEY) || "[]";
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function hasExchangedCode(code) {
  return loadExchangedCodes().includes(code);
}

function markCodeAsExchanged(code) {
  const current = loadExchangedCodes();
  if (current.includes(code)) {
    return;
  }
  const next = [...current, code].slice(-10);
  sessionStorage.setItem(EXCHANGED_CODES_STORAGE_KEY, JSON.stringify(next));
}

function isJwtLike(value) {
  return value.split(".").length === 3;
}

function randomBase64Url(bytes = 32) {
  const randomBytes = crypto.getRandomValues(new Uint8Array(bytes));
  return btoa(String.fromCharCode(...randomBytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

async function sha256Base64Url(input) {
  const encoded = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", encoded);
  return btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

async function exchangeCodeForTokens(code) {
  if (!COGNITO_DOMAIN || !COGNITO_CLIENT_ID) {
    return { tokens: null, error: "Missing Cognito domain/client configuration." };
  }
  const verifier = localStorage.getItem(PKCE_VERIFIER_STORAGE_KEY) || "";
  if (!verifier) {
    return { tokens: null, error: "Missing PKCE code_verifier in browser storage." };
  }

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: COGNITO_CLIENT_ID,
    redirect_uri: COGNITO_REDIRECT_URI,
    code,
    code_verifier: verifier,
  });
  const tokenEndpoint = `${trimTrailingSlash(COGNITO_DOMAIN)}/oauth2/token`;
  const response = await fetch(tokenEndpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!response.ok) {
    const responseBody = await response.text();
    return {
      tokens: null,
      error: `Token endpoint rejected the code (${response.status}). ${responseBody || "No response body."}`,
    };
  }
  const payload = await response.json();
  const idToken = payload.id_token || "";
  const accessToken = payload.access_token || "";
  if (!idToken && !accessToken) {
    return { tokens: null, error: "Token endpoint response did not include id_token or access_token." };
  }
  return { tokens: { idToken, accessToken }, error: "" };
}

function exchangeCodeForTokensOnce(code) {
  if (inFlightCodeExchange && inFlightCodeValue === code) {
    return inFlightCodeExchange;
  }
  inFlightCodeValue = code;
  inFlightCodeExchange = exchangeCodeForTokens(code).finally(() => {
    inFlightCodeExchange = null;
    inFlightCodeValue = "";
  });
  return inFlightCodeExchange;
}

function getBearerToken(session) {
  return session?.accessToken || session?.idToken || "";
}

function persistSession(session, setAuthToken) {
  localStorage.setItem(TOKEN_SESSION_STORAGE_KEY, JSON.stringify(session));
  const bearerToken = getBearerToken(session);
  localStorage.setItem(TOKEN_STORAGE_KEY, bearerToken);
  setAuthToken(bearerToken);
}

function loadInitialBearerToken() {
  const sessionRaw = localStorage.getItem(TOKEN_SESSION_STORAGE_KEY) || "";
  if (sessionRaw) {
    try {
      const parsed = JSON.parse(sessionRaw);
      return getBearerToken(parsed);
    } catch {
      return localStorage.getItem(TOKEN_STORAGE_KEY) || "";
    }
  }
  return localStorage.getItem(TOKEN_STORAGE_KEY) || "";
}

async function buildHostedLoginUrl() {
  if (!COGNITO_DOMAIN || !COGNITO_CLIENT_ID) {
    return "";
  }
  const verifier = randomBase64Url(64);
  const challenge = await sha256Base64Url(verifier);
  localStorage.setItem(PKCE_VERIFIER_STORAGE_KEY, verifier);
  const params = new URLSearchParams({
    response_type: "code",
    client_id: COGNITO_CLIENT_ID,
    redirect_uri: COGNITO_REDIRECT_URI,
    scope: "openid email profile",
    code_challenge_method: "S256",
    code_challenge: challenge,
  });
  return `${trimTrailingSlash(COGNITO_DOMAIN)}/oauth2/authorize?${params.toString()}`;
}

export default function App() {
  const [authToken, setAuthToken] = useState(loadInitialBearerToken());
  const [draftToken, setDraftToken] = useState("");
  const [loginUrl, setLoginUrl] = useState("");
  const [authHint, setAuthHint] = useState("");

  useEffect(() => {
    let mounted = true;

    async function initializeAuth() {
      const code = parseCodeFromSearch();
      if (code) {
        if (mounted && hasExchangedCode(code)) {
          setAuthHint(
            "This OAuth code was already used from this tab/session. Please sign in again to get a fresh code.",
          );
          return;
        }

        const cleanUrl = `${window.location.pathname}`;
        window.history.replaceState({}, document.title, cleanUrl);

        const { tokens, error } = await exchangeCodeForTokensOnce(code);
        if (tokens && mounted) {
          markCodeAsExchanged(code);
          persistSession(tokens, setAuthToken);
          localStorage.removeItem(PKCE_VERIFIER_STORAGE_KEY);
          setDraftToken("");
          return;
        }
        if (mounted) {
          setAuthHint(
            `Found OAuth code in URL but token exchange failed. ${error || ""} Please sign in again from this browser tab, or paste a JWT access/id token (not the code value).`,
          );
        }
      }

      if (COGNITO_DOMAIN && COGNITO_CLIENT_ID) {
        const generatedLoginUrl = await buildHostedLoginUrl();
        if (mounted) {
          setLoginUrl(generatedLoginUrl);
        }
      }

      const hashTokens = tokensFromHash();
      if (!hashTokens || !mounted) {
        return;
      }

      persistSession(hashTokens, setAuthToken);
      setDraftToken("");

      const nextUrl = `${window.location.pathname}${window.location.search}`;
      window.history.replaceState({}, document.title, nextUrl);
    }

    initializeAuth();
    return () => {
      mounted = false;
    };
  }, []);

  function saveDraftToken() {
    const candidate = draftToken.trim();
    if (!candidate) {
      return;
    }
    setAuthHint("");
    if (isJwtLike(candidate)) {
      persistSession({ accessToken: candidate, idToken: "" }, setAuthToken);
      setDraftToken("");
      return;
    }

    if (COGNITO_DOMAIN && COGNITO_CLIENT_ID) {
      exchangeCodeForTokens(candidate)
        .then(({ tokens }) => {
          if (tokens && getBearerToken(tokens)) {
            persistSession(tokens, setAuthToken);
            setDraftToken("");
            return;
          }
          setAuthHint(
            "The pasted value is not a JWT and could not be exchanged as an OAuth code. Paste the JWT access/id token from Cognito login response.",
          );
        })
        .catch(() => {
          setAuthHint(
            "Token exchange failed for pasted value. Paste a JWT access/id token, or complete hosted sign-in in this same browser tab.",
          );
        });
      return;
    }

    setAuthHint(
      "The pasted value does not look like a JWT bearer token. Paste an access/id token (three dot-separated segments), not the authorization code.",
    );
  }

  function signOut() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(TOKEN_SESSION_STORAGE_KEY);
    localStorage.removeItem(PKCE_VERIFIER_STORAGE_KEY);
    setAuthToken("");
    setDraftToken("");
  }

  return (
    <main className="app-shell">
      <header>
        <h1>Child Scheduler</h1>
        <p className="muted">Milestone 9: Cognito integration enabled</p>
        <p className="muted">API Base URL: {API_BASE_URL}</p>
      </header>

      <LoginPlaceholder
        authToken={authToken}
        draftToken={draftToken}
        loginUrl={loginUrl}
        onTokenChange={setDraftToken}
        onSaveToken={saveDraftToken}
        onSignOut={signOut}
        authHint={authHint}
      />
      <CatalogDebugPanel authToken={authToken} />
      <ScheduleConfigPanel authToken={authToken} />
      <ProfilePreferencesPanel authToken={authToken} />
    </main>
  );
}
