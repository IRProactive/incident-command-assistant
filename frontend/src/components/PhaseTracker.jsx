const PHASES = [
  { key: "preparation", label: "Preparation" },
  { key: "detection_analysis", label: "Detection & Analysis" },
  { key: "containment", label: "Containment" },
  { key: "eradication", label: "Eradication" },
  { key: "recovery", label: "Recovery" },
  { key: "post_incident_activity", label: "Post-Incident" },
];

export default function PhaseTracker({ activePhase = "detection_analysis" }) {
  return (
    <div className="phase-tracker" role="list" aria-label="Incident lifecycle phase (NIST SP 800-61r3)">
      {PHASES.map((phase) => (
        <div
          key={phase.key}
          role="listitem"
          className={`phase-step${phase.key === activePhase ? " active" : ""}`}
        >
          {phase.label}
        </div>
      ))}
    </div>
  );
}
