/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_IMAGE_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module 'node:fs' {
  export function readFileSync(path: string, encoding: string): string
}

declare module 'node:url' {
  export function fileURLToPath(url: string | URL): string
}
