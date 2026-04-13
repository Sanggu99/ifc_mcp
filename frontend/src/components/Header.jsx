import React from 'react';

export default function Header({ serverOnline }) {
  return (
    <header className="h-14 flex items-center justify-between px-5 border-b border-white/5 bg-surface-950/80 backdrop-blur-md z-50 shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg shadow-primary-500/20">
          <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
          </svg>
        </div>
        <div>
          <h1 className="text-sm font-bold tracking-tight text-white">IFC MCP Studio</h1>
          <p className="text-[10px] text-surface-500 -mt-0.5">BIM Processing & Analysis</p>
        </div>
      </div>

      {/* Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs text-surface-400">
          <span className={`status-dot ${serverOnline ? 'online' : 'offline'}`}></span>
          <span>{serverOnline ? 'Server Connected' : 'Server Offline'}</span>
        </div>
        <div className="h-6 w-px bg-white/10"></div>
        <span className="text-[10px] font-mono text-surface-500 bg-surface-800/50 px-2 py-0.5 rounded-md border border-white/5">
          IFC4 / MCP v1.0
        </span>
      </div>
    </header>
  );
}
