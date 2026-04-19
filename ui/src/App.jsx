import { useEffect, useState } from "react";
import { API_BASE_URL } from "./config";
import CatalogDebugPanel from "./components/CatalogDebugPanel";
import LoginPlaceholder from "./components/LoginPlaceholder";
import ProfilePreferencesPanel from "./components/ProfilePreferencesPanel";
import ScheduleConfigPanel from "./components/ScheduleConfigPanel";

const TOKEN_STORAGE_KEY = "childScheduler.uiAuthToken";

function tokenFromHash() {
  const hash = window.location.hash || "";
  if (!hash.startsWith("#")) {
    return "";
  }
  const params = new URLSearchParams(hash.slice(1));
  return params.get("id_token") || params.get("access_token") || "";
}

export default function App() {
  const [authToken, setAuthToken] = useState(localStorage.getItem(TOKEN_STORAGE_KEY) || "");
  const [draftToken, setDraftToken] = useState("");

  useEffect(() => {
    const hashToken = tokenFromHash();
    if (!hashToken) {
      return;
    }

    localStorage.setItem(TOKEN_STORAGE_KEY, hashToken);
    setAuthToken(hashToken);
    setDraftToken("");

    const nextUrl = `${window.location.pathname}${window.location.search}`;
    window.history.replaceState({}, document.title, nextUrl);
  }, []);

  function saveDraftToken() {
    const token = draftToken.trim();
    if (!token) {
      return;
    }
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
    setAuthToken(token);
    setDraftToken("");
  }

  function signOut() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setAuthToken("");
    setDraftToken("");
  }

  return (
    <main className="app-shell">
      <header>
        <h1>Child Scheduler</h1>
        <p className="muted">Milestone 9: Cognito integration bootstrap</p>
        <p className="muted">API Base URL: {API_BASE_URL}</p>
      </header>

      <LoginPlaceholder
        authToken={authToken}
        draftToken={draftToken}
        onTokenChange={setDraftToken}
        onSaveToken={saveDraftToken}
        onSignOut={signOut}
      />
      <CatalogDebugPanel authToken={authToken} />
      <ScheduleConfigPanel authToken={authToken} />
      <ProfilePreferencesPanel authToken={authToken} />
    </main>
  );
}
