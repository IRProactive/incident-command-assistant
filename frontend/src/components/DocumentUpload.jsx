import { useRef, useState } from "react";
import { uploadDocument } from "../api.js";

const ACCEPTED = ".pdf,.docx";

export default function DocumentUpload({ onUploaded }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function handleFiles(fileList) {
    setError(null);
    const files = Array.from(fileList);
    if (files.length === 0) return;

    setBusy(true);
    try {
      for (const file of files) {
        await uploadDocument(file);
      }
      onUploaded?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      {error && <div className="error-banner">{error}</div>}
      <div
        className={`dropzone${dragging ? " dragging" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
      >
        <div className="dropzone-label">
          {busy ? "Ingesting…" : "Drop the IR plan or supporting docs here, or click to browse"}
        </div>
        <div className="dropzone-hint">PDF or DOCX</div>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          multiple
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>
    </div>
  );
}
