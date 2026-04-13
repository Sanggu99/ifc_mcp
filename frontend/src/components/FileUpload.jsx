import React, { useState, useRef, useCallback } from 'react';
import { uploadFile, convertCadToIfc } from '../utils/api';

export default function FileUpload({ onFileUploaded, onConvertComplete }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [converting, setConverting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const allowedExtensions = ['.dxf', '.ifc'];

  const validateFile = (file) => {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedExtensions.includes(ext)) {
      return `지원하지 않는 파일 형식입니다 (${ext}). DXF 또는 IFC 파일만 업로드 가능합니다.`;
    }
    if (file.size > 100 * 1024 * 1024) {
      return '파일 크기는 100MB 이하여야 합니다.';
    }
    return null;
  };

  const handleUpload = useCallback(async (file) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setUploading(true);
    setUploadProgress('업로드 중...');

    try {
      const result = await uploadFile(file);
      setUploadProgress(null);
      setUploading(false);

      if (onFileUploaded) {
        onFileUploaded(result);
      }

      // Auto-convert DXF files
      if (file.name.toLowerCase().endsWith('.dxf')) {
        setConverting(true);
        setUploadProgress('IFC로 변환 중...');
        try {
          const convertResult = await convertCadToIfc(file.name);
          if (onConvertComplete) {
            onConvertComplete(convertResult);
          }
        } catch (convertErr) {
          setError(`변환 오류: ${convertErr.message}`);
        } finally {
          setConverting(false);
          setUploadProgress(null);
        }
      }
    } catch (err) {
      setError(err.message);
      setUploading(false);
      setUploadProgress(null);
    }
  }, [onFileUploaded, onConvertComplete]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleUpload(files[0]);
    }
  }, [handleUpload]);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      handleUpload(file);
    }
    e.target.value = '';
  };

  const isProcessing = uploading || converting;

  return (
    <div className="p-4">
      <div
        className={`upload-zone ${isDragOver ? 'drag-over' : ''} ${isProcessing ? 'pointer-events-none opacity-60' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !isProcessing && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".dxf,.ifc"
          className="hidden"
          onChange={handleFileSelect}
          id="file-upload-input"
        />

        {isProcessing ? (
          <div className="flex flex-col items-center gap-3">
            <div className="spinner"></div>
            <p className="text-sm text-primary-400 font-medium">{uploadProgress}</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <div className="w-12 h-12 rounded-xl bg-surface-800/60 flex items-center justify-center border border-white/5">
              <svg className="w-6 h-6 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-medium text-surface-300">
                파일을 드래그하거나 클릭하여 업로드
              </p>
              <p className="text-xs text-surface-500 mt-1">
                DXF → 자동 IFC 변환  ·  IFC → 직접 뷰어 로드
              </p>
            </div>
            <div className="flex gap-2 mt-1">
              <span className="badge badge-dxf">.DXF</span>
              <span className="badge badge-ifc">.IFC</span>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-3 p-3 rounded-lg bg-danger-500/10 border border-danger-500/20 text-danger-400 text-xs animate-slide-up">
          ⚠️ {error}
        </div>
      )}
    </div>
  );
}
