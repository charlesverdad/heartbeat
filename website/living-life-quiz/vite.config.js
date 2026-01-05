import { defineConfig } from 'vite'
import legacy from '@vitejs/plugin-legacy'
import { execSync } from 'child_process'
import { copyFileSync } from 'fs'
import { resolve } from 'path'

// Get git commit hash
function getGitHash() {
  try {
    return execSync('git rev-parse --short HEAD').toString().trim()
  } catch {
    return 'unknown'
  }
}

export default defineConfig({
  plugins: [
    legacy({
      targets: ['defaults', 'not IE 11']
    }),
    {
      name: 'copy-scoring-logic',
      writeBundle() {
        // Copy scoring-logic.js to dist directory
        copyFileSync(
          resolve(process.cwd(), 'scoring-logic.js'),
          resolve(process.cwd(), 'dist', 'scoring-logic.js')
        )
      }
    }
  ],
  define: {
    __APP_VERSION__: JSON.stringify(getGitHash())
  },
  root: '.',
  publicDir: 'public',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    rollupOptions: {
      input: {
        main: './index.html'
      }
    }
  },
  server: {
    port: 3000,
    open: true
  }
})
