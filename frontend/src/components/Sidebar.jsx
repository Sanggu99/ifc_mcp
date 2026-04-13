import React, { useState, useEffect, useCallback } from 'react';
import { fetchFiles, deleteFile, getFileUrl } from '../utils/api';

export default function Sidebar({ activeFile, onFileSelect, refreshTrigger }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expandedInfo, setExpandedInfo] = useState(null);

  const loadFiles = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchFiles();
      setFiles(result.files || []);
    } catch (err) {
      console.error('Failed to load files:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFiles();
  }, [loadFiles, refreshTrigger]);

  const handleDelete = async (filename, e) => {
    e.stopPropagation();
    if (!confirm(`"${filename}" 파일을 삭제하시겠습니까?`)) return;

    try {
      await deleteFile(filename);
      await loadFiles();
      if (activeFile === filename) {
        onFileSelect(null);
      }
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const handleDownload = (filename, e) => {
    e.stopPropagation();
    window.open(getFileUrl(filename), '_blank');
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const uploadFiles = files.filter((f) => f.source === 'upload');
  const outputFiles = files.filter((f) => f.source === 'output');

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5 shrink-0">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold text-surface-200 flex items-center gap-2">
            <svg className="w-4 h-4 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
            </svg>
            파일 관리
          </h3>
          <button
            onClick={loadFiles}
            className="p-1 rounded-md hover:bg-surface-700/50 transition-colors text-surface-500 hover:text-surface-300"
            title="새로고침"
            id="refresh-files-button"
          >
            <svg className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
            </svg>
          </button>
        </div>
      </div>

      {/* File list */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-4">
        {/* Output files */}
        {outputFiles.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-wider text-surface-500 font-semibold px-1 mb-1.5 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-accent-500"></span>
              생성된 IFC ({outputFiles.length})
            </p>
            <div className="space-y-0.5">
              {outputFiles.map((file) => (
                <FileItem
                  key={file.filename}
                  file={file}
                  isActive={activeFile === file.filename}
                  onSelect={() => onFileSelect(file.filename)}
                  onDelete={(e) => handleDelete(file.filename, e)}
                  onDownload={(e) => handleDownload(file.filename, e)}
                  expanded={expandedInfo === file.filename}
                  onToggleInfo={() =>
                    setExpandedInfo(
                      expandedInfo === file.filename ? null : file.filename
                    )
                  }
                  formatSize={formatSize}
                  formatTime={formatTime}
                />
              ))}
            </div>
          </div>
        )}

        {/* Upload files */}
        {uploadFiles.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-wider text-surface-500 font-semibold px-1 mb-1.5 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-warn-500"></span>
              업로드 파일 ({uploadFiles.length})
            </p>
            <div className="space-y-0.5">
              {uploadFiles.map((file) => (
                <FileItem
                  key={file.filename}
                  file={file}
                  isActive={activeFile === file.filename}
                  onSelect={() => onFileSelect(file.filename)}
                  onDelete={(e) => handleDelete(file.filename, e)}
                  onDownload={(e) => handleDownload(file.filename, e)}
                  expanded={expandedInfo === file.filename}
                  onToggleInfo={() =>
                    setExpandedInfo(
                      expandedInfo === file.filename ? null : file.filename
                    )
                  }
                  formatSize={formatSize}
                  formatTime={formatTime}
                />
              ))}
            </div>
          </div>
        )}

        {/* Empty state */}
        {files.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="w-12 h-12 rounded-xl bg-surface-800/40 flex items-center justify-center mb-3 border border-white/5">
              <svg className="w-6 h-6 text-surface-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>
            <p className="text-xs text-surface-500">아직 파일이 없습니다</p>
            <p className="text-[10px] text-surface-600 mt-0.5">DXF 또는 IFC 파일을 업로드하세요</p>
          </div>
        )}
      </div>
    </div>
  );
}

function FileItem({
  file,
  isActive,
  onSelect,
  onDelete,
  onDownload,
  expanded,
  onToggleInfo,
  formatSize,
  formatTime,
}) {
  const isIFC = file.type === 'IFC';

  return (
    <div>
      <div
        className={`file-item group ${isActive ? 'active' : ''}`}
        onClick={onSelect}
        id={`file-item-${file.filename.replace(/\./g, '-')}`}
      >
        {/* File icon */}
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mr-2.5 ${
          isIFC ? 'bg-accent-500/15 text-accent-400' : 'bg-warn-500/15 text-warn-400'
        }`}>
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
        </div>

        {/* File info */}
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-surface-200 truncate">{file.filename}</p>
          <p className="text-[10px] text-surface-500">{formatSize(file.size)}</p>
        </div>

        {/* Badge */}
        <span className={`badge ${isIFC ? 'badge-ifc' : 'badge-dxf'} mr-1.5`}>
          {file.type}
        </span>

        {/* Actions (visible on hover) */}
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={onDownload}
            className="p-1 rounded hover:bg-surface-600/50 text-surface-500 hover:text-surface-300"
            title="다운로드"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
          </button>
          <button
            onClick={onDelete}
            className="p-1 rounded hover:bg-danger-500/20 text-surface-500 hover:text-danger-400"
            title="삭제"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
