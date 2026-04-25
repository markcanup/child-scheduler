import { useState } from "react";
import RequestDiagnostics from "./RequestDiagnostics";
import { DEFAULT_HUB_ID } from "../config";
import { getScheduleConfig, putScheduleConfig } from "../services/api";

const DAYS_OF_WEEK = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];
const ACTION_TYPES = ["rule", "speech", "notify"];
const TIME_MODES = ["absolute", "relative"];

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

function createEmptySchedule() {
  const scheduleId =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `schedule-${Date.now()}`;

  return {
    scheduleId,
    name: "New schedule",
    enabled: true,
    daysOfWeek: ["MON"],
    timeMode: "absolute",
    baseTime: "07:00",
    actionType: "rule",
    parameters: {
      targetId: "",
    },
  };
}

function normalizeScheduleConfig(payload) {
  return {
    ...defaultPayload(),
    ...payload,
    meta: {
      timezone: "America/New_York",
      ...(payload?.meta || {}),
    },
    scheduleDefinitions: Array.isArray(payload?.scheduleDefinitions) ? payload.scheduleDefinitions : [],
    dayConfigs: Array.isArray(payload?.dayConfigs) ? payload.dayConfigs : [],
  };
}

function sanitizeSchedule(schedule) {
  const base = {
    ...schedule,
    scheduleId: schedule.scheduleId || createEmptySchedule().scheduleId,
    name: schedule.name || "Untitled schedule",
    enabled: Boolean(schedule.enabled),
    daysOfWeek: Array.isArray(schedule.daysOfWeek)
      ? schedule.daysOfWeek.filter((day) => DAYS_OF_WEEK.includes(day))
      : [],
    timeMode: TIME_MODES.includes(schedule.timeMode) ? schedule.timeMode : "absolute",
    baseTime: schedule.baseTime || "",
    relativeToScheduleId: schedule.relativeToScheduleId || "",
    offsetMinutes: Number.isFinite(schedule.offsetMinutes) ? schedule.offsetMinutes : 0,
    actionType: ACTION_TYPES.includes(schedule.actionType) ? schedule.actionType : "rule",
    parameters: typeof schedule.parameters === "object" && schedule.parameters ? { ...schedule.parameters } : {},
  };

  if (base.daysOfWeek.length === 0) {
    base.daysOfWeek = ["MON"];
  }

  if (base.actionType === "rule") {
    base.parameters = {
      targetId: base.parameters.targetId || "",
    };
  } else if (base.actionType === "speech") {
    base.parameters = {
      targetId: base.parameters.targetId || "",
      text: base.parameters.text || "",
    };
  } else if (base.actionType === "notify") {
    const targetIds = Array.isArray(base.parameters.targetIds) ? base.parameters.targetIds : [];
    base.parameters = {
      targetIds,
      text: base.parameters.text || "",
    };
  }

  if (base.timeMode === "absolute") {
    base.relativeToScheduleId = "";
  }

  return base;
}

export default function ScheduleConfigPanel({ authToken }) {
  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState("");
  const [diagnostics, setDiagnostics] = useState(null);
  const [scheduleConfig, setScheduleConfig] = useState(defaultPayload());
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [jsonText, setJsonText] = useState(JSON.stringify(defaultPayload(), null, 2));

  function setSchedules(nextSchedules) {
    setScheduleConfig((current) => ({
      ...current,
      scheduleDefinitions: nextSchedules,
    }));
  }

  function generateScheduleJson(config = scheduleConfig) {
    const generated = normalizeScheduleConfig(config);
    setJsonText(JSON.stringify(generated, null, 2));
    return generated;
  }

  function applyLoadedSchedule(data) {
    const normalized = normalizeScheduleConfig(data);
    const sanitizedSchedules = normalized.scheduleDefinitions.map(sanitizeSchedule);
    const nextConfig = {
      ...normalized,
      scheduleDefinitions: sanitizedSchedules,
    };

    setScheduleConfig(nextConfig);
    setSelectedIndex(sanitizedSchedules.length > 0 ? 0 : -1);
    generateScheduleJson(nextConfig);
  }

  async function loadScheduleConfig() {
    setStatus("loading");
    setMessage("");
    setDiagnostics(null);
    try {
      const data = await getScheduleConfig(authToken);
      applyLoadedSchedule(data);
      setStatus("success");
      setMessage("Schedule loaded.");
    } catch (err) {
      setStatus("error");
      setMessage(err.message);
      setDiagnostics(err.diagnostics || null);
    }
  }

  function generateFromEditor() {
    setStatus("success");
    setMessage("Generated JSON from editor state.");
    setDiagnostics(null);
    generateScheduleJson();
  }

  async function saveScheduleConfig() {
    setStatus("saving");
    setMessage("");
    setDiagnostics(null);

    const payload = generateScheduleJson();

    try {
      const response = await putScheduleConfig(payload, authToken);
      setStatus("success");
      setMessage(`Saved scheduleVersion ${response.scheduleVersion}.`);
      if (response.compiledPreview || response.brokenReferences) {
        setJsonText(
          JSON.stringify(
            {
              ...payload,
              compiledPreview: response.compiledPreview || [],
              brokenReferences: response.brokenReferences || [],
            },
            null,
            2,
          ),
        );
      }
    } catch (err) {
      setStatus("error");
      setMessage(err.message);
      setDiagnostics(err.diagnostics || null);
    }
  }

  function addSchedule() {
    const next = [...scheduleConfig.scheduleDefinitions, createEmptySchedule()];
    setSchedules(next);
    setSelectedIndex(next.length - 1);
  }

  function deleteSelectedSchedule() {
    if (selectedIndex < 0) {
      return;
    }

    const next = scheduleConfig.scheduleDefinitions.filter((_, index) => index !== selectedIndex);
    setSchedules(next);
    if (next.length === 0) {
      setSelectedIndex(-1);
    } else {
      setSelectedIndex(Math.min(selectedIndex, next.length - 1));
    }
  }

  function updateSelectedSchedule(updater) {
    if (selectedIndex < 0) {
      return;
    }

    const next = scheduleConfig.scheduleDefinitions.map((item, index) =>
      index === selectedIndex ? sanitizeSchedule(updater(item)) : item,
    );
    setSchedules(next);
  }

  const selectedSchedule =
    selectedIndex >= 0 && selectedIndex < scheduleConfig.scheduleDefinitions.length
      ? scheduleConfig.scheduleDefinitions[selectedIndex]
      : null;

  return (
    <section className="card">
      <h2>Schedule Config Editor</h2>
      <div className="row wrap">
        <button type="button" onClick={loadScheduleConfig} disabled={!authToken}>
          Load schedule config
        </button>
        <button type="button" onClick={generateFromEditor} disabled={!authToken}>
          Generate JSON
        </button>
        <button type="button" onClick={saveScheduleConfig} disabled={!authToken}>
          Save schedule config
        </button>
        <span className="muted">Status: {status}</span>
      </div>
      {!authToken && <p className="warning">Sign in first to load, generate, or save schedule config.</p>}
      {message && <p className={status === "error" ? "error" : "ok"}>{message}</p>}
      <RequestDiagnostics diagnostics={diagnostics} />

      <h3>Schedules</h3>
      <div className="row wrap">
        <button type="button" onClick={addSchedule} disabled={!authToken}>
          Add schedule
        </button>
        <button type="button" onClick={deleteSelectedSchedule} disabled={!authToken || selectedIndex < 0}>
          Delete selected
        </button>
      </div>

      <label>
        Select schedule
        <select
          value={selectedIndex >= 0 ? String(selectedIndex) : ""}
          onChange={(event) => setSelectedIndex(Number(event.target.value))}
          disabled={!authToken || scheduleConfig.scheduleDefinitions.length === 0}
        >
          {scheduleConfig.scheduleDefinitions.length === 0 && <option value="">No schedules</option>}
          {scheduleConfig.scheduleDefinitions.map((schedule, index) => (
            <option key={schedule.scheduleId || index} value={index}>
              {schedule.name || `Schedule ${index + 1}`} ({schedule.scheduleId})
            </option>
          ))}
        </select>
      </label>

      {selectedSchedule && (
        <div className="card nested-card">
          <label>
            Name
            <input
              value={selectedSchedule.name || ""}
              onChange={(event) =>
                updateSelectedSchedule((current) => ({
                  ...current,
                  name: event.target.value,
                }))
              }
            />
          </label>

          <label>
            Schedule ID
            <input
              value={selectedSchedule.scheduleId || ""}
              onChange={(event) =>
                updateSelectedSchedule((current) => ({
                  ...current,
                  scheduleId: event.target.value,
                }))
              }
            />
          </label>

          <label>
            Enabled
            <select
              value={selectedSchedule.enabled ? "true" : "false"}
              onChange={(event) =>
                updateSelectedSchedule((current) => ({
                  ...current,
                  enabled: event.target.value === "true",
                }))
              }
            >
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          </label>

          <label>
            Days of week (comma separated)
            <input
              value={(selectedSchedule.daysOfWeek || []).join(",")}
              onChange={(event) =>
                updateSelectedSchedule((current) => ({
                  ...current,
                  daysOfWeek: event.target.value
                    .split(",")
                    .map((value) => value.trim().toUpperCase())
                    .filter(Boolean),
                }))
              }
            />
          </label>

          <label>
            Time mode
            <select
              value={selectedSchedule.timeMode}
              onChange={(event) =>
                updateSelectedSchedule((current) => ({
                  ...current,
                  timeMode: event.target.value,
                }))
              }
            >
              {TIME_MODES.map((timeMode) => (
                <option key={timeMode} value={timeMode}>
                  {timeMode}
                </option>
              ))}
            </select>
          </label>

          {selectedSchedule.timeMode === "absolute" ? (
            <label>
              Base time (HH:mm)
              <input
                value={selectedSchedule.baseTime || ""}
                onChange={(event) =>
                  updateSelectedSchedule((current) => ({
                    ...current,
                    baseTime: event.target.value,
                  }))
                }
              />
            </label>
          ) : (
            <>
              <label>
                Relative to schedule ID
                <input
                  value={selectedSchedule.relativeToScheduleId || ""}
                  onChange={(event) =>
                    updateSelectedSchedule((current) => ({
                      ...current,
                      relativeToScheduleId: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Offset minutes
                <input
                  type="number"
                  value={selectedSchedule.offsetMinutes ?? 0}
                  onChange={(event) =>
                    updateSelectedSchedule((current) => ({
                      ...current,
                      offsetMinutes: Number(event.target.value),
                    }))
                  }
                />
              </label>
            </>
          )}

          <label>
            Action type
            <select
              value={selectedSchedule.actionType}
              onChange={(event) =>
                updateSelectedSchedule((current) => ({
                  ...current,
                  actionType: event.target.value,
                }))
              }
            >
              {ACTION_TYPES.map((actionType) => (
                <option key={actionType} value={actionType}>
                  {actionType}
                </option>
              ))}
            </select>
          </label>

          {selectedSchedule.actionType === "rule" && (
            <label>
              Rule targetId
              <input
                value={selectedSchedule.parameters?.targetId || ""}
                onChange={(event) =>
                  updateSelectedSchedule((current) => ({
                    ...current,
                    parameters: {
                      targetId: event.target.value,
                    },
                  }))
                }
              />
            </label>
          )}

          {selectedSchedule.actionType === "speech" && (
            <>
              <label>
                Speech targetId
                <input
                  value={selectedSchedule.parameters?.targetId || ""}
                  onChange={(event) =>
                    updateSelectedSchedule((current) => ({
                      ...current,
                      parameters: {
                        ...current.parameters,
                        targetId: event.target.value,
                      },
                    }))
                  }
                />
              </label>
              <label>
                Speech text
                <input
                  value={selectedSchedule.parameters?.text || ""}
                  onChange={(event) =>
                    updateSelectedSchedule((current) => ({
                      ...current,
                      parameters: {
                        ...current.parameters,
                        text: event.target.value,
                      },
                    }))
                  }
                />
              </label>
            </>
          )}

          {selectedSchedule.actionType === "notify" && (
            <>
              <label>
                Notify targetIds (comma separated)
                <input
                  value={Array.isArray(selectedSchedule.parameters?.targetIds) ? selectedSchedule.parameters.targetIds.join(",") : ""}
                  onChange={(event) =>
                    updateSelectedSchedule((current) => ({
                      ...current,
                      parameters: {
                        ...current.parameters,
                        targetIds: event.target.value
                          .split(",")
                          .map((value) => value.trim())
                          .filter(Boolean),
                      },
                    }))
                  }
                />
              </label>
              <label>
                Notify text
                <input
                  value={selectedSchedule.parameters?.text || ""}
                  onChange={(event) =>
                    updateSelectedSchedule((current) => ({
                      ...current,
                      parameters: {
                        ...current.parameters,
                        text: event.target.value,
                      },
                    }))
                  }
                />
              </label>
            </>
          )}
        </div>
      )}

      <h3>Generated JSON</h3>
      <textarea aria-label="Schedule config JSON" value={jsonText} readOnly rows={18} />
    </section>
  );
}
