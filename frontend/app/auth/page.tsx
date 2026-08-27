import React from "react";

export default function AuthPage() {
  return (
    <div style={{ maxWidth: 480, margin: "0 auto", padding: 24, border: "1px solid #334155", borderRadius: 16, background: "#111827" }}>
      <h2>Sign In</h2>
      <p>Email login, OAuth-ready flow, protected routes, and session management scaffolding.</p>
      <button style={{ marginTop: 12, padding: "10px 14px", borderRadius: 8 }}>Continue with Email</button>
    </div>
  );
}
