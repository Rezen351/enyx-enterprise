import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  // AeroponicDiagram.jsx is a raw SVG asset (XML) accidentally given a .jsx
  // extension and is not imported anywhere — exclude it from JS linting.
  globalIgnores([
    'dist',
    'src/components/Dashboard/Pages/AeroponicDiagram.jsx',
  ]),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      // The dashboard intentionally fetches data inside an effect on mount and
      // whenever filter deps change (Audit, ControlPanel, Alerts, …). This is a
      // deliberate, app-wide pattern — keep it as a warning rather than failing
      // lint. Refactor to useEffectEvent() if stricter enforcement is wanted.
      'react-hooks/set-state-in-effect': 'warn',
      // Context modules co-locate the Provider component with their useXxx hook
      // (ThemeContext, NotificationContext, ModuleContext). That is by design.
      'react-refresh/only-export-components': 'warn',
    },
  },
  {
    // Build/config files run in Node, not the browser.
    files: ['vite.config.js', '*.config.js', 'eslint.config.js', 'ui/screenshot-pages.js'],
    languageOptions: {
      globals: { ...globals.node },
    },
  },
])
