import React, { useState } from 'react';
import { createElement, modifyElement } from '../utils/api';

export default function ModelingPanel({ activeFile, selectedElement, onRefresh }) {
  const [activeTool, setActiveTool] = useState(null); // 'Wall', 'Column', 'Door', 'Window'
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const [formData, setFormData] = useState({
    height: 3.0,
    thickness: 0.2,
    radius: 0.2,
    width: 0.9,
    x1: 0, y1: 0, z1: 0,
    x2: 5, y2: 0, z2: 0,
    x: 0, y: 0, z: 0
  });

  const [pickMode, setPickMode] = useState(null); // 'start', 'end', 'pos'

  // Update coordinates from 3D viewer click
  React.useEffect(() => {
    if (selectedElement?.point) {
      const p = selectedElement.point;
      if (pickMode === 'start') {
        setFormData(prev => ({ ...prev, x1: p.x, y1: p.y, z1: p.z }));
        setPickMode(null);
      } else if (pickMode === 'end') {
        setFormData(prev => ({ ...prev, x2: p.x, y2: p.y, z2: p.z }));
        setPickMode(null);
      } else if (pickMode === 'pos') {
        setFormData(prev => ({ ...prev, x: p.x, y: p.y, z: p.z }));
        setPickMode(null);
      }
    }
  }, [selectedElement, pickMode]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: parseFloat(value) || 0 }));
  };

  const handleCreate = async () => {
    if (!activeFile || !activeTool) return;
    setLoading(true);
    setMessage(null);
    try {
      const res = await createElement(activeFile, activeTool, formData);
      if (res.success) {
        setMessage({ type: 'success', text: res.message });
        onRefresh();
      } else {
        setMessage({ type: 'error', text: res.message });
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleModifyAction = async (action, params = {}) => {
    if (!activeFile || !selectedElement) return;
    setLoading(true);
    setMessage(null);
    try {
      const res = await modifyElement(activeFile, selectedElement.expressID, action, params);
      if (res.success) {
        setMessage({ type: 'success', text: res.message });
        onRefresh();
      } else {
        setMessage({ type: 'error', text: res.message });
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-surface-950/80 backdrop-blur-md border-l border-white/5">
      <div className="p-4 border-b border-white/5 bg-surface-900/50">
        <h3 className="text-sm font-semibold text-surface-100 flex items-center gap-2">
          <svg className="w-4 h-4 text-accent-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
          </svg>
          Revit Modeling Tools
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Creation Tools */}
        <section className="space-y-3">
          <p className="text-[10px] uppercase font-bold text-surface-500 tracking-wider flex items-center gap-2">
            <span className="w-1 h-3 bg-accent-500 rounded-full"></span>
            객체 생성 (Create)
          </p>
          <div className="grid grid-cols-2 gap-2">
            {['Wall', 'Column', 'Door', 'Window'].map(tool => (
              <button
                key={tool}
                onClick={() => setActiveTool(activeTool === tool ? null : tool)}
                className={`p-2.5 rounded-xl border transition-all text-xs font-medium flex items-center justify-center gap-2 ${
                  activeTool === tool 
                  ? 'bg-accent-500/20 border-accent-500/50 text-accent-300 shadow-lg shadow-accent-500/10' 
                  : 'bg-surface-800/40 border-white/5 text-surface-400 hover:bg-surface-800 hover:text-surface-200'
                }`}
              >
                {tool === 'Wall' && '🧱 Wall'}
                {tool === 'Column' && '🏛️ Column'}
                {tool === 'Door' && '🚪 Door'}
                {tool === 'Window' && '🪟 Window'}
              </button>
            ))}
          </div>

          {activeTool && (
            <div className="glass-panel-light p-4 space-y-4 animate-in slide-in-from-top-2">
              <div className="grid grid-cols-2 gap-4">
                {(activeTool === 'Wall' || activeTool === 'Column' || activeTool === 'Door' || activeTool === 'Window') && (
                  <div className="space-y-1">
                    <label className="text-[10px] text-surface-500 ml-1">Height (m)</label>
                    <input type="number" name="height" value={formData.height} onChange={handleInputChange} className="input-field-sm" />
                  </div>
                )}
                {activeTool === 'Wall' && (
                  <div className="space-y-1">
                    <label className="text-[10px] text-surface-500 ml-1">Thickness (m)</label>
                    <input type="number" name="thickness" value={formData.thickness} onChange={handleInputChange} className="input-field-sm" />
                  </div>
                )}
                {activeTool === 'Column' && (
                  <div className="space-y-1">
                    <label className="text-[10px] text-surface-500 ml-1">Radius (m)</label>
                    <input type="number" name="radius" value={formData.radius} onChange={handleInputChange} className="input-field-sm" />
                  </div>
                )}
                {(activeTool === 'Door' || activeTool === 'Window') && (
                  <div className="space-y-1">
                    <label className="text-[10px] text-surface-500 ml-1">Width (m)</label>
                    <input type="number" name="width" value={formData.width} onChange={handleInputChange} className="input-field-sm" />
                  </div>
                )}
              </div>

              {activeTool === 'Wall' ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] text-accent-400/70 font-medium">Wall Path</p>
                    <div className="flex gap-1">
                      <button 
                        onClick={() => setPickMode('start')} 
                        className={`px-2 py-0.5 rounded text-[10px] border transition-colors ${pickMode === 'start' ? 'bg-accent-500 text-white' : 'bg-surface-800 text-surface-400 border-white/5'}`}
                      >
                        Pick Start
                      </button>
                      <button 
                        onClick={() => setPickMode('end')} 
                        className={`px-2 py-0.5 rounded text-[10px] border transition-colors ${pickMode === 'end' ? 'bg-accent-500 text-white' : 'bg-surface-800 text-surface-400 border-white/5'}`}
                      >
                        Pick End
                      </button>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <input type="number" name="x1" value={formData.x1.toFixed(2)} onChange={handleInputChange} placeholder="X1" className="input-field-sm" />
                    <input type="number" name="y1" value={formData.y1.toFixed(2)} onChange={handleInputChange} placeholder="Y1" className="input-field-sm" />
                    <input type="number" name="z1" value={formData.z1.toFixed(2)} onChange={handleInputChange} placeholder="Z1" className="input-field-sm" />
                    <input type="number" name="x2" value={formData.x2.toFixed(2)} onChange={handleInputChange} placeholder="X2" className="input-field-sm" />
                    <input type="number" name="y2" value={formData.y2.toFixed(2)} onChange={handleInputChange} placeholder="Y2" className="input-field-sm" />
                    <input type="number" name="z2" value={formData.z2.toFixed(2)} onChange={handleInputChange} placeholder="Z2" className="input-field-sm" />
                  </div>
                </div>
              ) : activeTool === 'Column' ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] text-accent-400/70 font-medium">Position</p>
                    <button 
                      onClick={() => setPickMode('pos')} 
                      className={`px-2 py-0.5 rounded text-[10px] border transition-colors ${pickMode === 'pos' ? 'bg-accent-500 text-white' : 'bg-surface-800 text-surface-400 border-white/5'}`}
                    >
                      Pick on Viewer
                    </button>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <input type="number" name="x" value={formData.x.toFixed(2)} onChange={handleInputChange} placeholder="X" className="input-field-sm" />
                    <input type="number" name="y" value={formData.y.toFixed(2)} onChange={handleInputChange} placeholder="Y" className="input-field-sm" />
                    <input type="number" name="z" value={formData.z.toFixed(2)} onChange={handleInputChange} placeholder="Z" className="input-field-sm" />
                  </div>
                </div>
              ) : (activeTool === 'Door' || activeTool === 'Window') && (
                <div className="bg-warn-500/10 border border-warn-500/20 p-2 rounded-lg text-center">
                  <p className="text-[10px] text-warn-400">
                    {selectedElement?.ifcType?.includes('Wall') 
                      ? `선택된 벽체(#${selectedElement.expressID})에 삽입됩니다.`
                      : '먼저 호스트가 될 벽체를 선택하세요.'}
                  </p>
                </div>
              )}

              <button
                onClick={handleCreate}
                disabled={loading || ((activeTool === 'Door' || activeTool === 'Window') && !selectedElement?.ifcType?.includes('Wall'))}
                className="w-full py-2 bg-accent-500 hover:bg-accent-400 disabled:bg-surface-700 disabled:text-surface-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-accent-500/20 flex items-center justify-center gap-2"
              >
                {loading ? <div className="spinner-xs" /> : '객체 생성하기'}
              </button>
            </div>
          )}
        </section>

        {/* Modification Tools (Inspector) */}
        <section className="space-y-3">
          <p className="text-[10px] uppercase font-bold text-surface-500 tracking-wider flex items-center gap-2">
            <span className="w-1 h-3 bg-warn-500 rounded-full"></span>
            선택된 객체 수정 (Modify)
          </p>
          
          {selectedElement ? (
            <div className="glass-panel-light p-4 space-y-4">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="text-[10px] text-surface-500 font-mono">ID: #{selectedElement.expressID}</p>
                  <p className="text-xs font-bold text-surface-200">{selectedElement.ifcType}</p>
                </div>
                <div className="badge badge-ifc uppercase text-[9px]">{selectedElement.ifcType?.replace('IFC', '')}</div>
              </div>

              <div className="grid grid-cols-3 gap-1">
                <button onClick={() => handleModifyAction('move', { dx: 1 })} className="btn-tool" title="+X 이동">X+</button>
                <button onClick={() => handleModifyAction('move', { dy: 1 })} className="btn-tool" title="+Y 이동">Y+</button>
                <button onClick={() => handleModifyAction('move', { dz: 1 })} className="btn-tool" title="+Z 이동">Z+</button>
                <button onClick={() => handleModifyAction('move', { dx: -1 })} className="btn-tool" title="-X 이동">X-</button>
                <button onClick={() => handleModifyAction('move', { dy: -1 })} className="btn-tool" title="-Y 이동">Y-</button>
                <button onClick={() => handleModifyAction('move', { dz: -1 })} className="btn-tool" title="-Z 이동">Z-</button>
              </div>

              <div className="h-px bg-white/5 my-3"></div>

              <div className="space-y-2">
                <button
                  onClick={() => handleModifyAction('delete')}
                  className="w-full py-2 bg-danger-500/10 hover:bg-danger-500/20 text-danger-400 rounded-xl text-xs font-medium border border-danger-500/20 transition-all flex items-center justify-center gap-2"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                  </svg>
                  요소 삭제 (Delete)
                </button>
              </div>
            </div>
          ) : (
            <div className="border border-dashed border-white/5 rounded-2xl p-8 text-center bg-surface-900/30">
              <svg className="w-8 h-8 text-surface-700 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.042 21.672L13.684 16.6m0 0l-2.51 2.225.569-3.447c.102-.62-.512-1.109-1.066-.812l-2.731 1.47 2.667-2.533c.458-.436.44-1.161-.031-1.574l-4.66-4.03 5.033.407c.615.05 1.05-.623.726-1.148L9.244 3.372 11.714 8.2c.252.491.944.505 1.212.027l2.315-4.084-1.148 5.032c-.149.65.417 1.255 1.056 1.185l4.305-.476-3.32 2.74c-.567.468-.451 1.35.209 1.651l4.337 2.008-4.128-1.108c-.658-.176-1.269.403-1.062 1.052l1.357 4.252z" />
              </svg>
              <p className="text-xs text-surface-600">3D 화면에서 수정할 객체를 선택하세요</p>
            </div>
          )}
        </section>

        {message && (
          <div className={`p-3 rounded-xl text-[10px] animate-fade-in ${
            message.type === 'success' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-danger-500/10 text-danger-400 border border-danger-500/20'
          }`}>
            {message.type === 'success' ? '✓' : '⚠'} {message.text}
          </div>
        )}
      </div>
    </div>
  );
}
