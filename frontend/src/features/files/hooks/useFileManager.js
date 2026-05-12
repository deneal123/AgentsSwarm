import { useCallback, useEffect, useState } from 'react';

export function useFileManager(mode = 'CHAT') {
  const [files, setFiles] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);

  const loadFiles = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { fetchUserFiles } = await import('@api/files');
      const data = await fetchUserFiles(mode);
      setFiles(Array.isArray(data?.files) ? data.files : []);
    } catch (err) {
      setError(err?.message || 'Не удалось загрузить файлы');
    } finally {
      setIsLoading(false);
    }
  }, [mode]);

  const uploadFile = useCallback(async (file) => {
    if (!file) return null;
    setIsUploading(true);
    setUploadProgress(0);
    setError(null);
    try {
      const { uploadFile: apiUpload } = await import('@api/files');
      const result = await apiUpload(mode, file, (pct) => setUploadProgress(pct));
      setFiles((prev) => [result, ...prev]);
      return result;
    } catch (err) {
      setError(err?.message || 'Не удалось загрузить файл');
      return null;
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  }, [mode]);

  const deleteFile = useCallback(async (fileId) => {
    setError(null);
    try {
      const { deleteFile: apiDelete } = await import('@api/files');
      await apiDelete(fileId);
      setFiles((prev) => prev.filter((f) => String(f.file_id) !== String(fileId)));
    } catch (err) {
      setError(err?.message || 'Не удалось удалить файл');
    }
  }, []);

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  return {
    files,
    isLoading,
    isUploading,
    uploadProgress,
    error,
    uploadFile,
    deleteFile,
    refresh: loadFiles,
  };
}
