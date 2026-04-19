import { useEffect, useMemo, useState } from "react";

function getDaysSince(isoDate) {
  if (!isoDate) {
    return null;
  }
  const rotatedAt = new Date(isoDate);
  if (Number.isNaN(rotatedAt.getTime())) {
    return null;
  }
  const now = new Date();
  const msPerDay = 1000 * 60 * 60 * 24;
  return Math.floor((now - rotatedAt) / msPerDay);
}

function parseJwtSubject(token) {
  try {
    const payload = token.split(".")[1];
    if (!payload) {
      return "local-user";
    }
    const decoded = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    return decoded.sub || decoded.email || "local-user";
  } catch {
    return "local-user";
  }
}

function storageKey(token) {
  return `childScheduler.profile.${parseJwtSubject(token)}`;
}

export default function ProfilePreferencesPanel({ authToken }) {
  const [psk, setPsk] = useState("");
  const [lastRotated, setLastRotated] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!authToken) {
      setPsk("");
      setLastRotated("");
      setSaved(false);
      return;
    }

    const raw = localStorage.getItem(storageKey(authToken));
    if (!raw) {
      setPsk("");
      setLastRotated("");
      setSaved(false);
      return;
    }

    try {
      const parsed = JSON.parse(raw);
      setPsk(parsed.hubitatPsk || "");
      setLastRotated(parsed.pskLastRotatedAt || "");
    } catch {
      setPsk("");
      setLastRotated("");
    }
  }, [authToken]);

  const keyAgeDays = useMemo(() => getDaysSince(lastRotated), [lastRotated]);
  const showWarning = keyAgeDays !== null && keyAgeDays >= 365;

  function savePreferences() {
    if (!authToken) {
      return;
    }

    const effectiveLastRotated = lastRotated || new Date().toISOString();
    setLastRotated(effectiveLastRotated);

    localStorage.setItem(
      storageKey(authToken),
      JSON.stringify({
        hubitatPsk: psk,
        pskLastRotatedAt: effectiveLastRotated,
      }),
    );
    setSaved(true);
  }

  return (
    <section className="card">
      <h2>Profile / Preferences</h2>
      <p>Authenticated flow for viewing/updating Hubitat PSK profile field (local storage placeholder).</p>
      {!authToken && <p className="warning">Sign in to view and edit Hubitat PSK preferences.</p>}
      <label>
        Hubitat PSK
        <input
          type="password"
          value={psk}
          onChange={(event) => {
            setPsk(event.target.value);
            setSaved(false);
          }}
          placeholder="Enter shared secret"
          disabled={!authToken}
        />
      </label>
      <label>
        PSK last rotated timestamp
        <input
          type="datetime-local"
          value={lastRotated ? lastRotated.slice(0, 16) : ""}
          onChange={(event) => {
            const value = event.target.value;
            setLastRotated(value ? new Date(value).toISOString() : "");
            setSaved(false);
          }}
          disabled={!authToken}
        />
      </label>
      <button type="button" onClick={savePreferences} disabled={!authToken}>
        Save preferences
      </button>
      {saved && <p className="ok">Preferences saved for authenticated user.</p>}
      <p className="muted">
        Last rotated: {lastRotated || "Not set"}
        {keyAgeDays !== null ? ` (${keyAgeDays} days ago)` : ""}
      </p>
      {showWarning && <p className="warning">Warning: PSK age is 365+ days. Rotate annually.</p>}
    </section>
  );
}
