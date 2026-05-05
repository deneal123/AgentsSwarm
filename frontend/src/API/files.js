import client from "./client";

export async function getFileDownloadUrl(fileId, { expirySec = 3600, signal } = {}) {
  const res = await client.get(`/api/ml/v1/files/${fileId}/download-url`, {
    params: { expiry_sec: expirySec },
    signal,
  });
  return res.data;
}
