/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DBGPT_API_BASE_URL?: string;
  readonly VITE_DIGITAL_TWIN_MODEL_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
