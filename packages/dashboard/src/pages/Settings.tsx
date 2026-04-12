// Copyright 2026 AgentStack Contributors
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useEffect } from "react";
import apiClient from "../lib/api";
import { useProject } from "../components/ProjectSwitcher";

const S = {
  card: { background: "#0d0d0d", border: "1px solid #1e1e1e", borderRadius: 8 } as React.CSSProperties,
  label: { fontSize: 11, color: "#555", letterSpacing: "0.06em", textTransform: "uppercase" as const, fontWeight: 500 },
  input: {
    width: "100%", background: "#111", border: "1px solid #222", borderRadius: 6,
    padding: "9px 12px", color: "#fff", fontSize: 13, outline: "none", boxSizing: "border-box" as const,
  } as React.CSSProperties,
};

interface Project { id: string; name: string; created_at: string; api_key_prefix?: string; }

const Settings: React.FC = () => {
  const { currentProject } = useProject();
  const [projects, setProjects] = useState<Project[]>([]);
  const [newName, setNewName] = useState("");
  const [newApiKey, setNewApiKey] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await apiClient.get("/projects");
      setProjects(res.data);
    } catch (err) {
      console.error("Failed to fetch projects:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      const res = await apiClient.post("/projects", { name: newName.trim() });
      if (res.data.api_key) {
        setNewApiKey(res.data.api_key);
      }
      setNewName("");
      fetchProjects();
      // Reload page to refresh project switcher
      setTimeout(() => window.location.reload(), 2000);
    } catch (err) {
      console.error("Failed to create project:", err);
      alert("Error creating project.");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this project? All trace data will be permanently erased.")) return;
    try {
      await apiClient.delete(`/projects/${id}`);
      fetchProjects();
      if (currentProject?.id === id) {
          window.location.reload();
      }
    } catch (err) {
      console.error("Failed to delete project:", err);
      alert("Error deleting project.");
    }
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div style={{ padding: "28px", maxWidth: 760 }}>
      <h1 style={{ fontSize: 20, fontWeight: 600, color: "#fff", marginBottom: 4 }}>Project Settings</h1>
      <p style={{ fontSize: 13, color: "#555", marginBottom: 24 }}>Manage API keys, projects, and account configuration.</p>

      {/* Create project */}
      <div style={{ ...S.card, padding: 20, marginBottom: 12 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: "#fff", marginBottom: 4 }}>Create New Project</div>
        <p style={{ fontSize: 12, color: "#555", marginBottom: 16 }}>Provision an isolated project scope for a new agent deployment.</p>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            style={{ ...S.input, flex: 1 }}
            type="text"
            placeholder="e.g. Production Main"
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleCreate()}
          />
          <button
            onClick={handleCreate}
            disabled={!newName.trim()}
            style={{
              background: newName.trim() ? "#fff" : "#222", color: newName.trim() ? "#000" : "#555",
              border: "none", borderRadius: 6, padding: "9px 18px", fontSize: 13, fontWeight: 600, cursor: "pointer",
            }}
          >Create</button>
        </div>

        {/* API key reveal */}
        {newApiKey && (
          <div style={{ marginTop: 16, background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.2)", borderRadius: 6, padding: 14 }}>
            <div style={{ fontSize: 12, color: "#22c55e", fontWeight: 600, marginBottom: 8 }}>✓ Project created! Save this API key — it won't be shown again</div>
            <div style={{ display: "flex", gap: 8 }}>
              <code style={{ flex: 1, fontSize: 12, fontFamily: "monospace", color: "#ccc", background: "#000", padding: "8px 12px", borderRadius: 4, wordBreak: "break-all", border: "1px solid #222" }}>
                {newApiKey}
              </code>
              <button
                onClick={() => handleCopy(newApiKey, "new")}
                style={{ background: "#222", border: "1px solid #333", borderRadius: 4, color: "#ccc", padding: "8px 12px", fontSize: 12, cursor: "pointer" }}
              >{copiedId === "new" ? "✓ Copied" : "Copy"}</button>
            </div>
          </div>
        )}
      </div>

      {/* Projects list */}
      <div style={{ ...S.card, overflow: "hidden" }}>
        <div style={{ padding: "14px 16px", borderBottom: "1px solid #1a1a1a" }}>
          <span style={S.label}>Active Projects ({projects.length})</span>
        </div>
        {loading ? (
             <div style={{ padding: 40, textAlign: "center", color: "#444", fontSize: 13 }}>Loading...</div>
        ) : projects.length === 0 ? (
          <div style={{ padding: 40, textAlign: "center", color: "#444", fontSize: 13 }}>
            No projects yet. Create one above to get started.
          </div>
        ) : (
          projects.map((project, i) => (
            <div key={project.id} style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "14px 16px", borderBottom: i < projects.length - 1 ? "1px solid #111" : "none",
            }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#fff", marginBottom: 3 }}>{project.name}</div>
                <div style={{ display: "flex", gap: 16 }}>
                  <span style={{ fontSize: 11, fontFamily: "monospace", color: "#444" }}>ID: {project.id}</span>
                  <span style={{ fontSize: 11, color: "#444" }}>Created: {new Date(project.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <button
                onClick={() => handleDelete(project.id)}
                style={{ background: "transparent", border: "1px solid #2a2a2a", borderRadius: 4, color: "#ef4444", fontSize: 12, padding: "5px 12px", cursor: "pointer" }}
              >Delete</button>
            </div>
          ))
        )}
      </div>

      {/* Account section */}
      <div style={{ ...S.card, padding: 20, marginTop: 12 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: "#fff", marginBottom: 16 }}>Account</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
          <div>
            <label style={{ ...S.label, display: "block", marginBottom: 6 }}>Email</label>
            <input style={S.input} type="email" defaultValue="user@agentstack.dev" />
          </div>
          <div>
            <label style={{ ...S.label, display: "block", marginBottom: 6 }}>Display Name</label>
            <input style={S.input} type="text" defaultValue="User" />
          </div>
        </div>
      </div>

      {/* Danger zone */}
      <div style={{ ...S.card, padding: 20, marginTop: 12, border: "1px solid rgba(239,68,68,0.2)" }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: "#ef4444", marginBottom: 4 }}>Danger Zone</div>
        <p style={{ fontSize: 12, color: "#555", marginBottom: 14 }}>Irreversible destructive actions. Proceed with caution.</p>
        <button
          onClick={() => { localStorage.removeItem("agentstack_token"); window.location.reload(); }}
          style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 6, padding: "8px 16px", fontSize: 12, cursor: "pointer" }}
        >Sign Out</button>
      </div>
    </div>
  );
};

export default Settings;
