const trimTrailingSlashes = (value: string) => value.replace(/\/+$/, '');

const DEFAULT_MODEL_ASSET_URL = new URL(
  '../../../3d model/7752d107551f622ecdb1894e4775dd58 (1).glb',
  import.meta.url,
).href;

export const API_BASE_URL = trimTrailingSlashes(import.meta.env.VITE_DBGPT_API_BASE_URL?.trim() || '');

export const DIGITAL_TWIN_MODEL_URL = import.meta.env.VITE_DIGITAL_TWIN_MODEL_URL?.trim() || DEFAULT_MODEL_ASSET_URL;

export const buildApiUrl = (path: string) => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
};
