import { useEffect, useState } from "react";
import { getSettings, updateSettings } from "../api.js";

export default function SettingsPanel() {
  const [provider, setProvider] = useState("none");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [configured, setConfigured] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);

  async function refresh() {
    try {
      const s = await getSettings();
      setProvider(s.provider);
      setModel(s.model);
      setConfigured(s.api_key_configured);
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleSave(e) {
    e.preventDefault();
    setError(null);
    setSaved(false);
    setSaving(true);
    try {
      const s = await updateSettings({ provider, apiKey, model });
      setConfigured(s.api_key_configured);
      setApiKey(""); // never keep the key sitting in the form after save
      setSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSave}>
      {error && <div className="error-banner">{error}</div>}
      <div className="form-row">
        <div className="form-field">
          <label htmlFor="provider">Provider</label>
          <select id="provider" value={provider} onChange={(e) => setProvider(e.target.value)}>
            <option value="none">None (retrieval only)</option>
            <option value="anthropic">Anthropic</option>
          </select>
        </div>
        <div className="form-field">
          <label htmlFor="model">Model</label>
          <input
            id="model"
            type="text"
            placeholder="claude-sonnet-4-5"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            disabled={provider !== "anthropic"}
          />
        </div>
        <div className="form-field">
          <label htmlFor="apiKey">API key</label>
          <input
            id="apiKey"
            type="password"
            placeholder={configured ? "••••••••  (configured — leave blank to keep)" : "sk-ant-..."}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            disabled={provider !== "anthropic"}
            autoComplete="off"
          />
        </div>
        <button type="submit" className="btn" disabled={saving}>
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
      <div className="settings-status">
        <span className={`status-dot${provider !== "none" && configured ? " on" : ""}`} />
        {provider === "none"
          ? "Retrieval only — no synthesized answers"
          : configured
          ? `Anthropic configured (${model || "default model"})`
          : "Anthropic selected, but no API key is set yet"}
        {saved && " — saved"}
      </div>
    </form>
  );
}
