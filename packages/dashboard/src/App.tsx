// Copyright 2026 AgentStack Contributors
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import { ProjectProvider, ProjectSwitcher } from "./components/ProjectSwitcher";

import Dashboard from "./pages/Dashboard";
import TraceView from "./pages/TraceView";
import { Security } from "./pages/Security";
import { Analytics } from "./pages/Analytics";
import Metrics from "./pages/Metrics";
import Settings from "./pages/Settings";

//  Inline SVG icons 
const IconLayers = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <polygon points="12 2 2 7 12 12 22 7 12 2"/>
    <polyline points="2 17 12 22 22 17"/>
    <polyline points="2 12 12 17 22 12"/>
  </svg>
);
const IconDashboard = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
    <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
    <rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>
  </svg>
);
const IconActivity = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
  </svg>
);
const IconBarChart = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
    <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>
    <line x1="6" y1="20" x2="6" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/>
  </svg>
);
const IconSettings = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
  </svg>
);

//  Nav Item 
const NavItem: React.FC<{ to: string; label: string; icon: React.ReactNode }> = ({ to, label, icon }) => {
  const location = useLocation();
  const isActive = location.pathname === to || (to !== "/" && location.pathname.startsWith(to));
  return (
    <Link
      to={to}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "10px",
        padding: "8px 12px",
        borderRadius: "6px",
        fontSize: "14px",
        fontWeight: 400,
        marginBottom: "2px",
        textDecoration: "none",
        color: isActive ? "#ffffff" : "#888888",
        background: isActive ? "rgba(255,255,255,0.07)" : "transparent",
        transition: "all 0.15s",
      }}
      onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.color = "#dddddd"; }}
      onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLElement).style.color = "#888888"; }}
    >
      <span style={{ opacity: isActive ? 1 : 0.6 }}>{icon}</span>
      {label}
    </Link>
  );
};

//  Sidebar 
const Sidebar: React.FC = () => (
  <aside style={{
    width: "180px",
    minWidth: "180px",
    height: "100vh",
    background: "#050505",
    borderRight: "1px solid #1a1a1a",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  }}>
    {/* Brand */}
    <div style={{ padding: "20px 16px 14px", borderBottom: "1px solid #1a1a1a" }}>
      <Link to="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: "10px" }}>
        <span style={{ color: "#888" }}><IconLayers /></span>
        <div>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "#fff", letterSpacing: "0.06em", lineHeight: 1.2 }}>AI AGENT</div>
          <div style={{ fontSize: "9px", color: "#555", letterSpacing: "0.08em", textTransform: "uppercase" }}>OBSERVABILITY</div>
        </div>
      </Link>
    </div>

    {/* Project Switcher */}
    <div style={{ padding: "8px 12px", borderBottom: "1px solid #1a1a1a" }}>
      <ProjectSwitcher />
    </div>

    {/* Search */}
    <div style={{ padding: "10px 12px" }}>
      <div style={{ position: "relative" }}>
        <svg style={{ position: "absolute", left: 8, top: "50%", transform: "translateY(-50%)", color: "#555" }} width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <input type="text" placeholder="Search" style={{
          width: "100%", background: "#111", border: "1px solid #222", borderRadius: "6px",
          padding: "6px 8px 6px 26px", fontSize: "12px", color: "#aaa", outline: "none",
          boxSizing: "border-box",
        }} />
      </div>
    </div>

    {/* Nav */}
    <nav style={{ flex: 1, padding: "4px 8px", overflowY: "auto" }}>
      <NavItem to="/" label="Dashboard" icon={<IconDashboard />} />
      <NavItem to="/traces" label="Traces" icon={<IconActivity />} />
      <NavItem to="/metrics" label="Metrics" icon={<IconBarChart />} />
      <NavItem to="/security" label="Security" icon={
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        </svg>
      } />
      <NavItem to="/settings" label="Settings" icon={<IconSettings />} />
    </nav>

    {/* User */}
    <div style={{ padding: "12px", borderTop: "1px solid #1a1a1a" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "6px 8px", borderRadius: "6px", cursor: "pointer" }}>
        <div style={{
          width: 28, height: 28, borderRadius: "50%", background: "#222",
          border: "1px solid #333", display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "12px", fontWeight: 600, color: "#aaa",
        }}>U</div>
        <span style={{ fontSize: "13px", color: "#ccc", fontWeight: 500 }}>User</span>
      </div>
    </div>
  </aside>
);

//  App 
const App: React.FC = () => {
  const isAuthenticated = localStorage.getItem("oxly_token") !== null || true;
  if (!isAuthenticated) return <LoginPage />;

  return (
    <ProjectProvider>
      <BrowserRouter>
        <div style={{ display: "flex", height: "100vh", width: "100vw", background: "#000", color: "#fff", fontFamily: "Inter, -apple-system, sans-serif", overflow: "hidden" }}>
          <Sidebar />
          <main style={{ flex: 1, height: "100%", overflowY: "auto", background: "#000" }}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/traces" element={<TraceView />} />
              <Route path="/metrics" element={<Metrics />} />
              <Route path="/security" element={<Security />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/deployments" element={<Dashboard />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="*" element={<div style={{ textAlign: "center", paddingTop: 80, color: "#555" }}>404  Not Found</div>} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </ProjectProvider>
  );
};

const LoginPage: React.FC = () => (
  <div style={{ minHeight: "100vh", background: "#000", display: "flex", alignItems: "center", justifyContent: "center" }}>
    <div style={{ width: 320 }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, textAlign: "center", marginBottom: 8 }}>Welcome Back</h1>
      <p style={{ color: "#666", textAlign: "center", marginBottom: 32, fontSize: 14 }}>Enter your credentials to access the platform</p>
      <form onSubmit={(e) => { e.preventDefault(); localStorage.setItem("oxly_token", "demo-token"); window.location.reload(); }}>
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", fontSize: 13, color: "#888", marginBottom: 6 }}>Email</label>
          <input type="email" placeholder="you@company.com" style={{ width: "100%", background: "#111", border: "1px solid #222", borderRadius: 8, padding: "10px 14px", color: "#fff", fontSize: 14, outline: "none", boxSizing: "border-box" }} required />
        </div>
        <div style={{ marginBottom: 24 }}>
          <label style={{ display: "block", fontSize: 13, color: "#888", marginBottom: 6 }}>Password</label>
          <input type="password" placeholder="" style={{ width: "100%", background: "#111", border: "1px solid #222", borderRadius: 8, padding: "10px 14px", color: "#fff", fontSize: 14, outline: "none", boxSizing: "border-box" }} required />
        </div>
        <button type="submit" style={{ width: "100%", background: "#fff", color: "#000", border: "none", borderRadius: 8, padding: "11px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>Sign In</button>
      </form>
    </div>
  </div>
);

export default App;
