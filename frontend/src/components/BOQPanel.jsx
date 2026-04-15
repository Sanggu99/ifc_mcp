import React, { useState, useCallback } from 'react';

const API_BASE = '/api';

async function fetchBOQ(filename) {
  const res = await fetch(`${API_BASE}/boq/${encodeURIComponent(filename)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'BOQ 조회 실패' }));
    throw new Error(err.detail || 'BOQ 조회에 실패했습니다.');
  }
  return res.json();
}

export default function BOQPanel({ activeFile }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedType, setExpandedType] = useState(null);

  const handleCalculate = useCallback(async () => {
    if (!activeFile || !activeFile.endsWith('.ifc')) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const result = await fetchBOQ(activeFile);
      setData(result.boq);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [activeFile]);

  const toggleType = (type) => {
    setExpandedType(expandedType === type ? null : type);
  };

  const formatVal = (val) =>
    typeof val === 'number' ? val.toFixed(3) : String(val ?? '-');

  const quantityKeys = ['Length', 'Area', 'GrossSideArea', 'NetSideArea', 'GrossVolume', 'NetVolume'];
  const quantityLabels = {
    Length: '길이 (m)',
    Area: '면적 (m²)',
    GrossSideArea: '외측면적 (m²)',
    NetSideArea: '내측면적 (m²)',
    GrossVolume: '총 체적 (m³)',
    NetVolume: '순 체적 (m³)',
  };

  const typeIcons = {
    IfcWall: '🧱',
    IfcWallStandardCase: '🧱',
    IfcSlab: '▬',
    IfcColumn: '🏛️',
    IfcBeam: '📐',
    IfcDoor: '🚪',
    IfcWindow: '🪟',
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-green-500 to-teal-500 flex items-center justify-center">
            <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 11h.01M12 11h.01M15 11h.01M4.929 4.929A10 10 0 1119.07 19.07M15 9h.01" />
            </svg>
          </div>
          <div>
            <h3 className="text-xs font-semibold text-surface-200">BOQ 물량 산출</h3>
            <p className="text-[10px] text-surface-500">
              {activeFile ? `📎 ${activeFile}` : '파일 미선택'}
            </p>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {/* Calculate Button */}
        <button
          onClick={handleCalculate}
          disabled={loading || !activeFile?.endsWith('.ifc')}
          className="w-full py-2.5 bg-gradient-to-r from-green-600 to-teal-600 hover:from-green-500 hover:to-teal-500 disabled:from-surface-700 disabled:to-surface-700 disabled:text-surface-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
              계산 중...
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7l-3.182-3.182a15.924 15.924 0 00-.582 3.249C4.432 15.246 3 18 3 18" />
              </svg>
              물량 산출 실행
            </>
          )}
        </button>

        {!activeFile?.endsWith('.ifc') && (
          <p className="text-[10px] text-surface-500 text-center">IFC 파일을 먼저 선택하세요.</p>
        )}

        {error && (
          <div className="bg-danger-500/10 border border-danger-500/20 rounded-xl p-3 text-[11px] text-danger-400">
            ⚠ {error}
          </div>
        )}

        {data && (
          <>
            {/* Summary Cards */}
            <div className="space-y-1">
              <p className="text-[10px] uppercase font-bold text-surface-500 tracking-wider flex items-center gap-2">
                <span className="w-1 h-3 bg-green-500 rounded-full"></span>
                타입별 요약
              </p>
              <div className="space-y-1.5">
                {Object.entries(data.summary || {}).map(([type, summary]) => (
                  <div key={type} className="rounded-xl border border-white/5 bg-surface-900/40 overflow-hidden">
                    {/* Type header */}
                    <button
                      className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-white/5 transition-colors"
                      onClick={() => toggleType(type)}
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-sm">{typeIcons[type] || '📦'}</span>
                        <span className="text-xs font-semibold text-surface-200">
                          {type.replace('Ifc', '')}
                        </span>
                        <span className="px-1.5 py-0.5 rounded-md bg-surface-800 text-surface-400 text-[10px] font-mono">
                          {summary.count}개
                        </span>
                      </div>
                      <svg
                        className={`w-3 h-3 text-surface-500 transition-transform ${expandedType === type ? 'rotate-180' : ''}`}
                        fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>

                    {/* Quantity details */}
                    {expandedType === type && (
                      <div className="border-t border-white/5 px-3 py-2 grid grid-cols-2 gap-x-4 gap-y-1.5">
                        {quantityKeys.map((key) => {
                          const val = summary[key];
                          if (!val || val === 0) return null;
                          return (
                            <div key={key} className="flex flex-col">
                              <span className="text-[9px] text-surface-500 uppercase tracking-wide">{quantityLabels[key]}</span>
                              <span className="text-[12px] font-mono text-teal-300 font-semibold">{formatVal(val)}</span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Total summary */}
            {Object.keys(data.summary || {}).length > 0 && (
              <div className="bg-gradient-to-br from-green-500/10 to-teal-500/10 border border-green-500/20 rounded-xl p-3 space-y-1.5">
                <p className="text-[10px] text-green-400 font-bold uppercase tracking-wider">전체 합산</p>
                {(() => {
                  const totals = {};
                  Object.values(data.summary || {}).forEach((s) => {
                    quantityKeys.forEach((k) => {
                      totals[k] = (totals[k] || 0) + (s[k] || 0);
                    });
                  });
                  return quantityKeys.map((k) =>
                    totals[k] > 0 ? (
                      <div key={k} className="flex justify-between items-center">
                        <span className="text-[10px] text-surface-400">{quantityLabels[k]}</span>
                        <span className="text-[11px] font-mono text-green-300 font-bold">{formatVal(totals[k])}</span>
                      </div>
                    ) : null
                  );
                })()}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
