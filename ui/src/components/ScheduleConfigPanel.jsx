import { useState } from "react";
import { DEFAULT_HUB_ID } from "../config";
import { getScheduleConfig, putScheduleConfig } from "../services/api";

function defaultPayload() {
  return {
    hubId: DEFAULT_HUB_ID,
    meta: {
      timezone: "America/New_York",
    },
    scheduleDefinitions: [],
    dayConfigs: [],
  };
}

export default function ScheduleConfigPanel({ authToken }) {
  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState("");
  const [jsonText, setJsonText] = useState(JSON.stringify(defaultPayload(), null, 2));

  async function loadScheduleConfig() {
    setStatus("loading");
    setMessage("");
    try {
      const data = await getScheduleConfig(authToken);
      setJsonText(JSON.stringify(data, null, 2));
      setStatus("success");
    } catch (err) {
      setStatus("error");
      setMessage(err.message);
    }
  }

  async function saveScheduleConfig() {
    setStatus("saving");
    setMessage("");

    let payload;
    try {
      payload = JSON.parse(jsonText);
    } catch {
      setStatus("error");
      setMessage("Schedule config JSON is invalid.");
      return;
    }

    try {
      const response = await putScheduleConfig(payload, authToken);
      setStatus("success");
      setMessage(`Saved scheduleVersion ${response.scheduleVersion}.`);
    } catch (err) {
      setStatus("error");
      setMessage(err.message);
    }
  }

  return (
    <section className="card">
      <h2>Schedule Config Viewer</h2>
      <div className="row">
        <button type="button" onClick={loadScheduleConfig} disabled={!authToken}>
          Load schedule config
        </button>
        <button type="button" onClick={saveScheduleConfig} disabled={!authToken}>
          Save schedule config
        </button>
        <span className="muted">Status: {status}</span>
      </div>
      {!authToken && <p className="warning">Sign in first to load or save schedule config.</p>}
      {message && <p className={status === "error" ? "error" : "ok"}>{message}</p>}
      <textarea
        aria-label="Schedule config JSON"
        value={jsonText}
        onChange={(event) => setJsonText(event.target.value)}
        rows={18}
      />
    </section>
  );
}
