import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import FileUpload from './components/FileUpload';
import IFCViewer from './components/IFCViewer';
import ChatPanel from './components/ChatPanel';
import Sidebar from './components/Sidebar';
import ModelingPanel from './components/ModelingPanel';
import BOQPanel from './components/BOQPanel';
import { checkHealth } from './utils/api';

export default function App() {
  const [activeFile, setActiveFile] = useState(null);
  const [serverOnline, setServerOnline] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'modeling' | 'boq'
  const [selectedElement, setSelectedElement] = useState(null);

  // Check server health
  useEffect(() => {
    const check = async () => {
      const online = await checkHealth();
      setServerOnline(online);
    };
    check();
    const interval = setInterval(check, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleFileUploaded = useCallback((result) => {
    setRefreshTrigger((prev) => prev + 1);
    if (result.filename && result.filename.endsWith('.ifc')) {
      setActiveFile(result.filename);
      setSelectedElement(null);
    }
  }, []);

  const handleConvertComplete = useCallback((result) => {
    setRefreshTrigger((prev) => prev + 1);
    if (result.output_file) {
      setActiveFile(result.output_file);
      setSelectedElement(null);
    }
  }, []);

  const handleModelActionComplete = useCallback(() => {
    setRefreshTrigger((prev) => prev + 1);
    setSelectedElement(null);
  }, []);

  const handleFileSelect = useCallback((filename) => {
    setActiveFile(filename);
    setSelectedElement(null);
  }, []);

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-surface-950">
      {/* Header */}
      <Header serverOnline={serverOnline} />

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar — File Management */}
        <div
          className={`${sidebarCollapsed ? 'w-0' : 'w-72'} transition-all duration-300 border-r border-white/5 bg-surface-950/50 flex flex-col shrink-0 overflow-hidden`}
        >
          {/* File Upload */}
          <FileUpload
            onFileUploaded={handleFileUploaded}
            onConvertComplete={handleConvertComplete}
          />

          {/* Divider */}
          <div className="h-px bg-white/5 mx-4"></div>

          {/* File List */}
          <div className="flex-1 overflow-hidden">
            <Sidebar
              activeFile={activeFile}
              onFileSelect={handleFileSelect}
              refreshTrigger={refreshTrigger}
            />
          </div>
        </div>

        {/* Sidebar Toggle */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="w-5 flex items-center justify-center border-r border-white/5 bg-surface-950 hover:bg-surface-800/50 transition-colors text-surface-600 hover:text-surface-400 shrink-0"
          title={sidebarCollapsed ? '사이드바 열기' : '사이드바 닫기'}
          id="sidebar-toggle"
        >
          <svg
            className={`w-3 h-3 transition-transform ${sidebarCollapsed ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
        </button>

        {/* Center — 3D Viewer */}
        <div className="flex-1 p-3 overflow-hidden relative">
          <IFCViewer 
            activeFile={activeFile} 
            refreshTrigger={refreshTrigger} 
            onSelectElement={setSelectedElement}
          />
        </div>

        {/* Right Panel Toggle */}
        <button
          onClick={() => setRightPanelCollapsed(!rightPanelCollapsed)}
          className="w-5 flex items-center justify-center border-l border-white/5 bg-surface-950 hover:bg-surface-800/50 transition-colors text-surface-600 hover:text-surface-400 shrink-0"
          title={rightPanelCollapsed ? '패널 열기' : '패널 닫기'}
          id="right-panel-toggle"
        >
          <svg
            className={`w-3 h-3 transition-transform ${rightPanelCollapsed ? '' : 'rotate-180'}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
        </button>

        {/* Right Panel — Chat & Modeling */}
        <div
          className={`${rightPanelCollapsed ? 'w-0' : 'w-96'} transition-all duration-300 border-l border-white/5 bg-surface-950/50 overflow-hidden shrink-0 flex flex-col`}
        >
          {/* Tabs */}
          <div className="flex border-b border-white/5 bg-surface-900/40 p-1 gap-1 shrink-0">
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex-1 py-1.5 text-[11px] font-bold rounded-lg transition-all flex items-center justify-center gap-2 ${
                activeTab === 'chat' 
                ? 'bg-primary-600 text-white shadow-lg' 
                : 'text-surface-500 hover:bg-white/5 hover:text-surface-300'
              }`}
            >
              💬 AI Assistant
            </button>
            <button
              onClick={() => setActiveTab('modeling')}
              className={`flex-1 py-1.5 text-[11px] font-bold rounded-lg transition-all flex items-center justify-center gap-2 ${
                activeTab === 'modeling' 
                ? 'bg-accent-600 text-white shadow-lg' 
                : 'text-surface-500 hover:bg-white/5 hover:text-surface-300'
              }`}
            >
              🏗️ Modeling
            </button>
            <button
              onClick={() => setActiveTab('boq')}
              className={`flex-1 py-1.5 text-[11px] font-bold rounded-lg transition-all flex items-center justify-center gap-2 ${
                activeTab === 'boq'
                ? 'bg-green-700 text-white shadow-lg'
                : 'text-surface-500 hover:bg-white/5 hover:text-surface-300'
              }`}
            >
              📊 BOQ
            </button>
          </div>

          <div className="flex-1 overflow-hidden">
            {activeTab === 'chat' ? (
              <ChatPanel
                activeFile={activeFile}
                selectedElement={selectedElement}
                onModelModified={handleModelActionComplete}
              />
            ) : activeTab === 'modeling' ? (
              <ModelingPanel
                activeFile={activeFile}
                selectedElement={selectedElement}
                onRefresh={handleModelActionComplete}
              />
            ) : (
              <BOQPanel activeFile={activeFile} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
