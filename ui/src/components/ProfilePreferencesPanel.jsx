import { useMemo, useState } from "react";

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

export default function ProfilePreferencesPanel() {
  const [psk, setPsk] = useState("");
  const [lastRotated, setLastRotated] = useState("");
  const [saved, setSaved] = useState(false);

  const keyAgeDays = useMemo(() => getDaysSince(lastRotated), [lastRotated]);
  const showWarning = keyAgeDays !== null && keyAgeDays >= 365;

  function savePreferences() {
    if (!lastRotated) {
      setLastRotated(new Date().toISOString());
    }
    setSaved(true);
  }

  return (
    <section className="card">
      <h2>Profile / Preferences</h2>
      <p>Hubitat PSK preference (temporary local UI state for Milestone 8).</p>
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
        />
      </label>
      <button type="button" onClick={savePreferences}>
        Save preferences
      </button>
      {saved && <p className="ok">Preferences saved (UI placeholder only).</p>}
      <p className="muted">
        Last rotated: {lastRotated || "Not set"}
        {keyAgeDays !== null ? ` (${keyAgeDays} days ago)` : ""}
      </p>
      {showWarning && <p className="warning">Warning: PSK age is 365+ days. Rotate annually.</p>}
    </section>
  );
}
