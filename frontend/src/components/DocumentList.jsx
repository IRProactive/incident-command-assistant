function formatTime(iso) {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function DocumentList({ documents }) {
  if (!documents || documents.length === 0) {
    return <p className="empty-state">No documents loaded yet.</p>;
  }

  return (
    <ul className="doc-list">
      {documents.map((doc) => (
        <li key={doc.id} className="doc-row">
          <span className="doc-name" title={doc.filename}>
            {doc.filename}
          </span>
          <span className="doc-meta">
            {doc.status === "ingested" && <span>{doc.chunk_count} chunks</span>}
            {doc.status === "failed" && doc.error && (
              <span title={doc.error}>{doc.error.slice(0, 40)}</span>
            )}
            <span>{formatTime(doc.uploaded_at)}</span>
            <span className={`status-badge ${doc.status}`}>{doc.status}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}
