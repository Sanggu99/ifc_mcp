import React, { useState, useRef, useEffect, useCallback } from 'react';
import { sendChatMessage } from '../utils/api';

export default function ChatPanel({ activeFile, selectedElement, onModelModified }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '안녕하세요! IFC 처리 도우미입니다. 🏗️\n\n다음 작업을 도와드릴 수 있습니다:\n• 📐 **CAD→IFC 변환**: DXF 파일을 IFC로 변환\n• 📊 **IFC 분석**: 모델 구조/속성 분석\n• ✏️ **IFC 수정**: 요소 이동, 속성 변경, 삭제\n\n파일을 업로드하고 원하는 작업을 말씀해주세요!',
    },
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || sending) return;

    // Add user message
    const userMessage = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setSending(true);

    try {
      // Build history for context
      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const result = await sendChatMessage(text, activeFile, history, selectedElement?.expressID);

      let assistantContent = result.response || '응답을 받지 못했습니다.';

      // If there's a tool result, append summary
      if (result.tool_result) {
        const tr = result.tool_result;

        if (tr.output_file) {
          assistantContent += `\n\n✅ **생성된 파일**: \`${tr.output_file}\``;
        }
        if (tr.stats) {
          const s = tr.stats;
          assistantContent += `\n📊 벽: ${s.walls || 0}개, 슬래브: ${s.slabs || 0}개, 기둥: ${s.columns || 0}개`;
        }
        if (tr.modified_count !== undefined) {
          assistantContent += `\n✏️ **수정된 요소**: ${tr.modified_count}개`;
        }
        if (tr.summary) {
          assistantContent += '\n\n**모델 요약:**';
          for (const [type, count] of Object.entries(tr.summary)) {
            assistantContent += `\n• ${type}: ${count}개`;
          }
        }

        // Trigger viewer refresh if something was modified
        if (tr.output_file || tr.modified_count > 0) {
          if (onModelModified) {
            onModelModified(tr);
          }
        }
      }

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: assistantContent },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `❌ 오류가 발생했습니다: ${err.message}`,
        },
      ]);
    } finally {
      setSending(false);
    }
  }, [input, sending, messages, activeFile, selectedElement, onModelModified]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Quick action buttons
  const quickActions = [
    { label: '📊 모델 분석', prompt: '현재 모델을 분석해줘' },
    { label: '📐 구조 보기', prompt: '모델의 공간 구조를 보여줘' },
    { label: '🧱 벽 목록', prompt: '모든 벽의 목록을 보여줘' },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Chat header */}
      <div className="px-4 py-3 border-b border-white/5 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
            <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
            </svg>
          </div>
          <div>
            <h3 className="text-xs font-semibold text-surface-200">AI 어시스턴트</h3>
            <p className="text-[10px] text-surface-500">
              {activeFile ? `📎 ${activeFile}` : '파일 미선택'}
            </p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3" id="chat-messages-container">
        {messages.map((msg, idx) => (
          <div key={idx} className={`chat-message ${msg.role}`}>
            <div className="whitespace-pre-wrap break-words">{formatMessage(msg.content)}</div>
          </div>
        ))}

        {sending && (
          <div className="chat-message assistant">
            <div className="flex items-center gap-2">
              <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }}></div>
              <span className="text-surface-400 text-xs">생각 중...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick actions */}
      {activeFile && (
        <div className="px-4 pb-2 shrink-0">
          <div className="flex gap-1.5 flex-wrap">
            {quickActions.map((action, idx) => (
              <button
                key={idx}
                className="text-[10px] px-2 py-1 rounded-md bg-surface-800/60 text-surface-400 border border-white/5 hover:bg-surface-700/60 hover:text-surface-300 transition-all"
                onClick={() => {
                  setInput(action.prompt);
                  inputRef.current?.focus();
                }}
                id={`quick-action-${idx}`}
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="px-4 pb-4 pt-2 border-t border-white/5 shrink-0">
        <div className="flex gap-2 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={activeFile ? '메시지를 입력하세요...' : '파일을 먼저 업로드해주세요'}
            className="input-field resize-none min-h-[40px] max-h-[120px]"
            rows={1}
            disabled={sending}
            id="chat-input"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sending}
            className="btn-primary shrink-0 px-3 py-2.5 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:transform-none"
            id="chat-send-button"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * 간단한 마크다운 볼드 포맷 처리
 */
function formatMessage(text) {
  if (!text) return '';

  // Simple bold formatting: **text** → <strong>text</strong>
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={i} className="font-semibold text-primary-300">
          {part.slice(2, -2)}
        </strong>
      );
    }
    // Inline code: `text`
    const codeParts = part.split(/(`.*?`)/g);
    return codeParts.map((cp, j) => {
      if (cp.startsWith('`') && cp.endsWith('`')) {
        return (
          <code
            key={`${i}-${j}`}
            className="bg-surface-800/60 text-accent-400 px-1.5 py-0.5 rounded text-xs font-mono"
          >
            {cp.slice(1, -1)}
          </code>
        );
      }
      return cp;
    });
  });
}
