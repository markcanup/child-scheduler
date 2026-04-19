import { useState } from "react";
import { getCatalog } from "../services/api";

export default function CatalogDebugPanel() {
  const [status, setStatus] = useState("idle");
  const [catalog, setCatalog] = useState(null);
  const [error, setError] = useState("");

  async function loadCatalog() {
    setStatus("loading");
    setError("");
    try {
      const data = await getCatalog();
      setCatalog(data);
      setStatus("success");
    } catch (err) {
      setStatus("error");
      setError(err.message);
    }
  }

  return (
    <section className="card">
      <h2>Catalog Status / Debug</h2>
      <div className="row">
        <button type="button" onClick={loadCatalog}>
          Load catalog
        </button>
        <span className="muted">Status: {status}</span>
      </div>
      {error && <p className="error">{error}</p>}
      <pre>{catalog ? JSON.stringify(catalog, null, 2) : "No catalog loaded yet."}</pre>
    </section>
  );
}
