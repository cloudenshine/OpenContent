import tseslint from 'typescript-eslint';
import obsidianmd from 'eslint-plugin-obsidianmd';

export default [{
  files: ['plugin/**/*.js'],
  ignores: ['**/*.test.*'],
  languageOptions: {
    parser: tseslint.parser,
    parserOptions: { project: './tsconfig.compat.json', tsconfigRootDir: import.meta.dirname },
  },
  plugins: { obsidianmd },
  rules: { 'obsidianmd/no-unsupported-api': 'error' },
}];
