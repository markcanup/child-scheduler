import { API_BASE_URL } from "./config";
import CatalogDebugPanel from "./components/CatalogDebugPanel";
import LoginPlaceholder from "./components/LoginPlaceholder";
import ProfilePreferencesPanel from "./components/ProfilePreferencesPanel";
import ScheduleConfigPanel from "./components/ScheduleConfigPanel";

export default function App() {
  return (
    <main className="app-shell">
      <header>
        <h1>Child Scheduler</h1>
        <p className="muted">Minimal UI bootstrap (Milestone 8)</p>
        <p className="muted">API Base URL: {API_BASE_URL}</p>
      </header>

      <LoginPlaceholder />
      <CatalogDebugPanel />
      <ScheduleConfigPanel />
      <ProfilePreferencesPanel />
    </main>
  );
}
