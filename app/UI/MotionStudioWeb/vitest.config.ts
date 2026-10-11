import { configDefaults, defineConfig, mergeConfig } from 'vitest/config'

import viteConfig from './vite.config'

export default defineConfig((env) => mergeConfig(viteConfig(env), {
  test: {
    // Executed explicitly by npm run test:chrome using its native node:test runner.
    exclude: [...configDefaults.exclude, 'src-tauri/src/project-window-chrome.test.cjs'],
  },
}))
