import { useEffect, useState, useCallback } from "react";
import PhaseTracker from "./components/PhaseTracker.jsx";
import DocumentUpload from "./components/DocumentUpload.jsx";
import DocumentList from "./components/DocumentList.jsx";
import SettingsPanel from "./components/SettingsPanel.jsx";
import AskPanel from "./components/AskPanel.jsx";
import { listDocuments } from "./api.js";

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [loadError, setLoadError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const docs = await listDocuments();
      setDocuments(docs);
      setLoadError(null);
    } catch (e) {
      setLoadError(e.message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Incident Command</h1>
        <span className="subtitle">ref: NIST SP 800-61r3</span>
      </header>

      <PhaseTracker activePhase="detection_analysis" />

      <section className="panel">
        <h2>Load documentation</h2>
        <p className="panel-hint">
          Upload the incident response plan and any supporting playbooks. Each is parsed and
          indexed so guidance can cite the specific section it's drawing from.
        </p>
        <DocumentUpload onUploaded={refresh} />
      </section>

      <section className="panel">
        <h2>Loaded documents</h2>
        {loadError && <div className="error-banner">{loadError}</div>}
        <DocumentList documents={documents} />
      </section>

      <section className="panel">
        <h2>LLM settings</h2>
        <p className="panel-hint">
          Configure a provider to turn retrieved passages into a synthesized answer. The key is
          held in memory only — it's cleared on restart and never written to disk.
        </p>
        <SettingsPanel />
      </section>

      <section className="panel">
        <h2>Ask</h2>
        <p className="panel-hint">
          Ask a question. Guidance is grounded in your loaded plan and NIST SP 800-61r3 —
          answers distinguish between the two.
        </p>
        <AskPanel />
      </section>
    </div>
  );
}
