# Dependency remediation (2026-08-13)

The MotionStudio web/Tauri dependency graph was refreshed with native package-manager commands.

- npm lockfile updates include the patched versions of Axios, Vite, Vitest, React Router, `@remix-run/router`, `brace-expansion`, `esbuild`, `form-data`, `js-yaml`, and PostCSS.
- React Router is updated to 7.18.2; the obsolete v7 `future` prop was removed from `src/App.tsx`.
- Cargo updates `serde_with` to 3.21.0.

`glib` remains on the 0.18 GTK line because the Tauri dependency graph requires `gtk ^0.18`; forcing `glib 0.20` cannot be resolved. Clearing that alert requires a coordinated GTK/Tauri upgrade and is intentionally left as a separate migration.

Validation:

- `npm audit --package-lock-only --ignore-scripts` reports zero vulnerabilities.
- `npm run build` passes.
- `cargo check --manifest-path app/UI/MotionStudioWeb/src-tauri/Cargo.toml` passes.
