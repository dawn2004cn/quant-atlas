/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_WS_GATEWAY_URL?: string;
  readonly VITE_ENABLE_SOCKETIO?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
