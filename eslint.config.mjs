import obsidianmd from 'eslint-plugin-obsidianmd';

export default [
  { ignores: ['dist/**', '**/*.test.*', 'tests/**', 'scripts/**'] },
  ...obsidianmd.configs.recommended,
  {
    files: ['plugin/**/*.js'],
    rules: {
      // Obsidian loads main.js as CommonJS; this project also deliberately
      // exposes pure CommonJS engines to Node. Keep the rule at error and
      // allow only the exact desktop host modules used by those files.
      '@typescript-eslint/no-require-imports': ['error', { allow: ['^(obsidian|child_process|path|fs|crypto|electron)$'] }],
      // Proper product/language names keep their canonical casing. Other UI
      // text still follows the official sentence-case rule.
      'obsidianmd/ui/sentence-case': ['warn', { brands: ['OpenContent', 'Codex', 'Claude', 'Python', 'Obsidian', 'Markdown'] }],
    },
  },
];
