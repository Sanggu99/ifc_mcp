/**
 * API Client — Backend REST API와의 통신 유틸리티
 */

const API_BASE = '/api';

/**
 * 파일 업로드
 */
export async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '업로드 실패' }));
    throw new Error(error.detail || '파일 업로드에 실패했습니다.');
  }

  return response.json();
}

/**
 * 파일 목록 조회
 */
export async function fetchFiles() {
  const response = await fetch(`${API_BASE}/files`);
  if (!response.ok) throw new Error('파일 목록을 불러올 수 없습니다.');
  return response.json();
}

/**
 * 파일 다운로드 URL 반환
 */
export function getFileUrl(filename) {
  return `${API_BASE}/files/${encodeURIComponent(filename)}`;
}

/**
 * 파일 삭제
 */
export async function deleteFile(filename) {
  const response = await fetch(`${API_BASE}/files/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('파일 삭제에 실패했습니다.');
  return response.json();
}

/**
 * CAD→IFC 변환
 */
export async function convertCadToIfc(filename, options = {}) {
  const response = await fetch(`${API_BASE}/convert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      filename,
      wall_height: options.wallHeight || 3.0,
      wall_thickness: options.wallThickness || 0.2,
      slab_thickness: options.slabThickness || 0.3,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '변환 실패' }));
    throw new Error(error.detail || 'CAD→IFC 변환에 실패했습니다.');
  }

  return response.json();
}

/**
 * LLM 채팅
 */
export async function sendChatMessage(message, filename = null, history = [], contextId = null) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      filename,
      history,
      context_id: contextId,
    }),
  });

  if (!response.ok) {
    throw new Error('채팅 요청에 실패했습니다.');
  }

  return response.json();
}

/**
 * 서버 상태 확인
 */
export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * BIM 객체 생성 (수동)
 */
export async function createElement(filename, type, parameters) {
  const response = await fetch(`${API_BASE}/model/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, type, parameters }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '생성 실패' }));
    throw new Error(error.detail || '객체 생성에 실패했습니다.');
  }

  return response.json();
}

/**
 * BIM 객체 수정 (수동)
 */
export async function modifyElement(filename, expressId, action, parameters) {
  const response = await fetch(`${API_BASE}/model/modify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, express_id: expressId, action, parameters }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '수정 실패' }));
    throw new Error(error.detail || '객체 수정에 실패했습니다.');
  }

  return response.json();
}
