import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      // The API layer returns loosely typed payloads; typing every endpoint is
      // tracked work, so keep these visible as warnings instead of failing lint.
      '@typescript-eslint/no-explicit-any': 'warn',
      // Flags the ordinary fetch-on-mount pattern (an async loader that sets state
      // after its await). A data-fetching library would be the real fix.
      'react-hooks/set-state-in-effect': 'warn',
    },
  },
])
