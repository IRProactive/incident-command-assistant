const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:5001";

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Upload failed (${res.status})`);
  }
  return res.json();
}

export async function listDocuments() {
  const res = await fetch(`${API_BASE}/documents/`);
  if (!res.ok) throw new Error(`Failed to load documents (${res.status})`);
  return res.json();
}

export async function getSettings() {
  const res = await fetch(`${API_BASE}/settings/`);
  if (!res.ok) throw new Error(`Failed to load settings (${res.status})`);
  return res.json();
}

export async function updateSettings({ provider, apiKey, model }) {
  const res = await fetch(`${API_BASE}/settings/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, api_key: apiKey || null, model: model || null }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Failed to update settings (${res.status})`);
  }
  return res.json();
}

export async function askGuidance(question, incidentId = "default") {
  const res = await fetch(`${API_BASE}/guidance/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ incident_id: incidentId, question }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Ask failed (${res.status})`);
  }
  return res.json();
}
