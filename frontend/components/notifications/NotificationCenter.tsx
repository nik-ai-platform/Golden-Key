import React from "react";

const notifications = [
  "Value Alert",
  "Live Opportunity",
  "Model Update",
  "Portfolio Warning",
  "System Notice",
];

export function NotificationCenter() {
  return (
    <div style={{ padding: 16, borderRadius: 12, background: "#111827", border: "1px solid #334155" }}>
      <h3>Notifications</h3>
      <ul>
        {notifications.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
