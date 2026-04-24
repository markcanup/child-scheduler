import { useEffect, useMemo, useState } from "react";
import { getScheduleConfig } from "../services/api";

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

export default function ProfilePreferencesPanel({ authToken }) {
  const [status, setStatus] = useState("idle");
  const [lastRotated, setLastRotated] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let mounted = true;

    async function loadTokenRotation() {
      if (!authToken) {
        setStatus("idle");
        setLastRotated("");
        setMessage("");
        return;
      }

      setStatus("loading");
      setMessage("");
      try {
        const config = await getScheduleConfig(authToken);
        if (!mounted) {
          return;
        }
        const rotatedAt = config?.security?.hubitatTokenLastRotatedAt || "";
        setLastRotated(rotatedAt);
        setStatus("success");
      } catch {
        if (!mounted) {
          return;
        }
        setLastRotated("");
        setStatus("error");
        setMessage("Could not load Hubitat token rotation metadata from backend.");
      }
    }

    loadTokenRotation();
    return () => {
      mounted = false;
    };
  }, [authToken]);

  const keyAgeDays = useMemo(() => getDaysSince(lastRotated), [lastRotated]);
  const showWarning = keyAgeDays !== null && keyAgeDays >= 365;

  return (
    <section className="card">
      <h2>Profile / Preferences</h2>
      <p>
        Hubitat shared secret rotation is managed in AWS deployment configuration. The UI no longer allows viewing
        or editing the token value.
      </p>
      {!authToken && <p className="warning">Sign in to view Hubitat token rotation status.</p>}
      {status === "loading" && <p className="muted">Loading token rotation status...</p>}
      {status === "error" && <p className="warning">{message}</p>}
      <p className="muted">
        Last rotated: {lastRotated || "Not set"}
        {keyAgeDays !== null ? ` (${keyAgeDays} days ago)` : ""}
      </p>
      {showWarning && <p className="warning">Warning: PSK age is 365+ days. Rotate annually.</p>}
    </section>
  );
}
