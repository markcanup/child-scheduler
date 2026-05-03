import { useState } from "react";
import RequestDiagnostics from "./RequestDiagnostics";
import { DEFAULT_HUB_ID } from "../config";
import { getCatalog, getScheduleConfig, putScheduleConfig } from "../services/api";

const DAYS_OF_WEEK = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];
const ACTION_TYPES = ["rule", "speech", "notify"];
const TIME_MODES = ["absolute", "relative"];
const RESOURCE_TYPE_ALIASES = {
  rule: "rule",
  speech: "speechTarget",
  speechtarget: "speechTarget",
  notify: "notifyDevice",
  notifydevice: "notifyDevice",
};

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
    dayTimes: { MON: "07:00" },
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

function normalizeCatalogResource(resource) {
  const rawType = resource?.type || resource?.resourceType || "";
  const normalizedType = RESOURCE_TYPE_ALIASES[String(rawType).toLowerCase()] || rawType;
  const resourceId = resource?.resourceId || "";
  const inferredType = resourceId.includes(":")
    ? RESOURCE_TYPE_ALIASES[resourceId.split(":")[0].toLowerCase()] || ""
    : "";

  return {
    ...resource,
    resourceId,
    type: normalizedType || inferredType,
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
    dayTimes:
      schedule.dayTimes && typeof schedule.dayTimes === "object"
        ? Object.fromEntries(
            Object.entries(schedule.dayTimes).filter(
              ([day, time]) => DAYS_OF_WEEK.includes(day) && typeof time === "string",
            ),
          )
        : {},
    timeMode: TIME_MODES.includes(schedule.timeMode) ? schedule.timeMode : "absolute",
    baseTime: schedule.baseTime || "",
    relativeToScheduleId: schedule.relativeToScheduleId || "",
    offsetMinutes: Number.isFinite(schedule.offsetMinutes) ? schedule.offsetMinutes : 0,
    actionType: ACTION_TYPES.includes(schedule.actionType) ? schedule.actionType : "rule",
    parameters: typeof schedule.parameters === "object" && schedule.parameters ? { ...schedule.parameters } : {},
  };

  if (base.daysOfWeek.length === 0 && Object.keys(base.dayTimes).length === 0) {
    base.daysOfWeek = ["MON"];
  }
  if (Object.keys(base.dayTimes).length === 0 && base.baseTime && base.daysOfWeek.length > 0) {
    base.dayTimes = Object.fromEntries(base.daysOfWeek.map((day) => [day, base.baseTime]));
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
    base.offsetMinutes = 0;
  } else {
    base.baseTime = "";
    base.dayTimes = {};
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
  const [catalogResources, setCatalogResources] = useState([]);
  const [catalogLoadedAt, setCatalogLoadedAt] = useState(0);
  const [compiledSummary, setCompiledSummary] = useState([]);

  function setSchedules(nextSchedules) {
    setScheduleConfig((current) => ({
      ...current,
      scheduleDefinitions: nextSchedules,
    }));
  }

  function generateScheduleJson(config = scheduleConfig) {
    const normalized = normalizeScheduleConfig(config);
    const cleanedDefinitions = normalized.scheduleDefinitions.map((schedule) => {
      const sanitized = sanitizeSchedule(schedule);
      const base = {
        scheduleId: sanitized.scheduleId,
        name: sanitized.name,
        enabled: sanitized.enabled,
        daysOfWeek: sanitized.daysOfWeek,
        timeMode: sanitized.timeMode,
        actionType: sanitized.actionType,
      };

      if (sanitized.timeMode === "absolute") {
        base.dayTimes = sanitized.dayTimes;
      } else {
        base.relativeToScheduleId = sanitized.relativeToScheduleId;
        base.offsetMinutes = sanitized.offsetMinutes;
      }

      if (sanitized.actionType === "rule") {
        base.parameters = {
          targetId: sanitized.parameters?.targetId || "",
        };
      } else if (sanitized.actionType === "speech") {
        base.parameters = {
          targetId: sanitized.parameters?.targetId || "",
          text: sanitized.parameters?.text || "",
        };
      } else {
        base.parameters = {
          targetIds: Array.isArray(sanitized.parameters?.targetIds) ? sanitized.parameters.targetIds : [],
          text: sanitized.parameters?.text || "",
        };
      }

      return base;
    });

    const generated = {
      ...normalized,
      scheduleDefinitions: cleanedDefinitions,
    };
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
    setCompiledSummary([]);
  }

  async function loadScheduleConfig({ forceRefreshCatalog = false } = {}) {
    setStatus("loading");
    setMessage("");
    setDiagnostics(null);
    try {
      const shouldRefreshCatalog =
        forceRefreshCatalog || catalogResources.length === 0 || Date.now() - catalogLoadedAt > 5 * 60 * 1000;
      const [data, catalog] = await Promise.all([
        getScheduleConfig(authToken),
        shouldRefreshCatalog ? getCatalog(authToken) : Promise.resolve(null),
      ]);
      applyLoadedSchedule(data);
      if (shouldRefreshCatalog) {
        setCatalogResources(Array.isArray(catalog?.resources) ? catalog.resources.map(normalizeCatalogResource) : []);
        setCatalogLoadedAt(Date.now());
      }
      setStatus("success");
      setMessage(`Schedule loaded${shouldRefreshCatalog ? " with catalog refresh" : ""}.`);
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
    const generated = generateScheduleJson();
    const summaryByDay = DAYS_OF_WEEK.map((day) => {
      const events = generated.scheduleDefinitions
        .filter((schedule) => {
          if (!schedule.enabled) return false;
          if (schedule.timeMode === "absolute") {
            return Boolean(schedule.dayTimes?.[day]);
          }
          return true;
        })
        .map((schedule) => {
          const when =
            schedule.timeMode === "absolute"
              ? schedule.dayTimes?.[day] || "N/A"
              : `relative to ${schedule.relativeToScheduleId || "unselected"} (${schedule.offsetMinutes || 0} min)`;
          return {
            scheduleId: schedule.scheduleId,
            name: schedule.name || schedule.scheduleId,
            when,
            actionType: schedule.actionType,
          };
        });
      return { day, events };
    });
    setCompiledSummary(summaryByDay);
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
        const previewByDay = {};
        (response.compiledPreview || []).forEach((event) => {
          if (!previewByDay[event.date]) {
            previewByDay[event.date] = [];
          }
          previewByDay[event.date].push(event);
        });
        const ordered = Object.keys(previewByDay)
          .sort()
          .map((date) => ({
            day: date,
            events: previewByDay[date].map((event) => ({
              scheduleId: event.sourceScheduleId,
              name: event.sourceScheduleId,
              when: event.time,
              actionType: event.actionType,
            })),
          }));
        setCompiledSummary(ordered);
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

  function updateSelectedScheduleDays(dayCode, checked) {
    updateSelectedSchedule((current) => {
      const existingDays = Array.isArray(current.daysOfWeek) ? current.daysOfWeek : [];
      const nextDays = checked
        ? [...new Set([...existingDays, dayCode])]
        : existingDays.filter((day) => day !== dayCode);
      return {
        ...current,
        daysOfWeek: nextDays,
        dayTimes: Object.fromEntries(
          Object.entries(current.dayTimes || {}).filter(([day]) => nextDays.includes(day)),
        ),
      };
    });
  }

  function updateSelectedScheduleDayTime(dayCode, timeValue) {
    updateSelectedSchedule((current) => ({
      ...current,
      dayTimes: {
        ...(current.dayTimes || {}),
        [dayCode]: timeValue,
      },
    }));
  }

  const selectedSchedule =
    selectedIndex >= 0 && selectedIndex < scheduleConfig.scheduleDefinitions.length
      ? scheduleConfig.scheduleDefinitions[selectedIndex]
      : null;
  const relativeScheduleOptions = scheduleConfig.scheduleDefinitions.filter(
    (schedule, index) => index !== selectedIndex && Boolean(schedule.scheduleId),
  );
  const ruleTargets = catalogResources.filter((resource) => resource.type === "rule");
  const speechTargets = catalogResources.filter((resource) => resource.type === "speechTarget");
  const notifyTargets = catalogResources.filter((resource) => resource.type === "notifyDevice");

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

          <div className="row schedule-id-row">
            <label className="checkbox-inline">
              <input
                type="checkbox"
                checked={Boolean(selectedSchedule.enabled)}
                onChange={(event) =>
                  updateSelectedSchedule((current) => ({
                    ...current,
                    enabled: event.target.checked,
                  }))
                }
              />
              Enabled
            </label>
            <span className="muted schedule-id-text">Schedule ID: {selectedSchedule.scheduleId || "N/A"}</span>
          </div>

          <fieldset className="day-grid-fieldset">
            <legend>Days of week</legend>
            {selectedSchedule.timeMode === "relative" && (
              <p className="muted">Relative schedules inherit applicable days from the linked schedule.</p>
            )}
            <div className="day-grid">
              {DAYS_OF_WEEK.map((day) => (
                <label key={day} className="day-option">
                  <span>{day}</span>
                  <input
                    type="checkbox"
                    checked={Array.isArray(selectedSchedule.daysOfWeek) && selectedSchedule.daysOfWeek.includes(day)}
                    onChange={(event) => updateSelectedScheduleDays(day, event.target.checked)}
                    disabled={selectedSchedule.timeMode === "relative"}
                  />
                </label>
              ))}
            </div>
          </fieldset>

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
            <fieldset className="day-grid-fieldset">
              <legend>Time by day (HH:mm)</legend>
              {Array.isArray(selectedSchedule.daysOfWeek) &&
                selectedSchedule.daysOfWeek.map((day) => (
                  <label key={`time-${day}`}>
                    {day}
                    <input
                      value={selectedSchedule.dayTimes?.[day] || ""}
                      onChange={(event) => updateSelectedScheduleDayTime(day, event.target.value)}
                    />
                  </label>
                ))}
            </fieldset>
          ) : (
            <>
              <label>
                Relative to schedule ID
                <select
                  value={selectedSchedule.relativeToScheduleId || ""}
                  onChange={(event) =>
                    updateSelectedSchedule((current) => ({
                      ...current,
                      relativeToScheduleId: event.target.value,
                    }))
                  }
                >
                  <option value="">Select schedule</option>
                  {relativeScheduleOptions.map((schedule) => (
                    <option key={schedule.scheduleId} value={schedule.scheduleId}>
                      {schedule.name || schedule.scheduleId} ({schedule.scheduleId})
                    </option>
                  ))}
                </select>
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
              <select
                value={selectedSchedule.parameters?.targetId || ""}
                onChange={(event) =>
                  updateSelectedSchedule((current) => ({
                    ...current,
                    parameters: {
                      targetId: event.target.value,
                    },
                  }))
                }
              >
                <option value="">Select rule target</option>
                {ruleTargets.map((resource) => (
                  <option key={resource.resourceId} value={resource.resourceId}>
                    {resource.label || resource.resourceId} ({resource.resourceId})
                  </option>
                ))}
              </select>
            </label>
          )}

          {selectedSchedule.actionType === "speech" && (
            <>
              <label>
                Speech targetId
                <select
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
                >
                  <option value="">Select speech target</option>
                  {speechTargets.map((resource) => (
                    <option key={resource.resourceId} value={resource.resourceId}>
                      {resource.label || resource.resourceId} ({resource.resourceId})
                    </option>
                  ))}
                </select>
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
                Notify targetIds
                <select
                  multiple
                  className="multiselect"
                  value={Array.isArray(selectedSchedule.parameters?.targetIds) ? selectedSchedule.parameters.targetIds : []}
                  onChange={(event) =>
                    updateSelectedSchedule((current) => ({
                      ...current,
                      parameters: {
                        ...current.parameters,
                        targetIds: Array.from(event.target.selectedOptions, (option) => option.value),
                      },
                    }))
                  }
                >
                  <option disabled value="">
                    Select one or more notify targets
                  </option>
                  {notifyTargets.map((resource) => (
                    <option key={resource.resourceId} value={resource.resourceId}>
                      {resource.label || resource.resourceId} ({resource.resourceId})
                    </option>
                  ))}
                </select>
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
      <h3>Compiled Schedule Summary</h3>
      {compiledSummary.length === 0 ? (
        <p className="muted">Press Generate to see a day-by-day summary.</p>
      ) : (
        <div className="summary-grid">
          {compiledSummary.map((daySummary) => (
            <div key={daySummary.day} className="summary-day">
              <h4>{daySummary.day}</h4>
              {daySummary.events.length === 0 ? (
                <p className="muted">No enabled events.</p>
              ) : (
                <ul>
                  {daySummary.events.map((event, idx) => (
                    <li key={`${daySummary.day}-${event.scheduleId}-${idx}`}>
                      <strong>{event.when}</strong> — {event.name} ({event.actionType})
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
