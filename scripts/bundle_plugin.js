/**
 * Validate and prepare community-directory-compatible plugin files.
 * Obsidian community installs only download main.js, manifest.json, and styles.css.
 * Validates that main.js is fully self-contained with no relative require() statements.
 */
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const pluginDir = path.join(root, 'plugin');
const mainJs = fs.readFileSync(path.join(pluginDir, 'main.js'), 'utf8');
const manifest = JSON.parse(fs.readFileSync(path.join(pluginDir, 'manifest.json'), 'utf8'));

if (mainJs.includes("require('./engine/") || mainJs.includes("require('../plugin/engine/")) {
  throw new Error('plugin/main.js still requires external engine modules');
}

const packageVersion = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8')).version;
const kernelVersion = fs.readFileSync(path.join(root, 'opencontent', '__init__.py'), 'utf8').match(/__version__ = "([^"]+)"/)?.[1];
if (packageVersion !== manifest.version || kernelVersion !== manifest.version) {
  throw new Error('Application package, plugin manifest and kernel versions must match');
}

const outDir = path.join(root, 'dist', 'community');
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, 'main.js'), mainJs);
fs.writeFileSync(path.join(outDir, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
fs.copyFileSync(path.join(pluginDir, 'styles.css'), path.join(outDir, 'styles.css'));

// Also ensure root manifest.json and versions.json are synchronized
fs.writeFileSync(path.join(root, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
const versionsFile = path.join(root, 'versions.json');
const versions = fs.existsSync(versionsFile) ? JSON.parse(fs.readFileSync(versionsFile, 'utf8')) : {};
versions[manifest.version] = manifest.minAppVersion;
fs.writeFileSync(path.join(root, 'versions.json'), JSON.stringify(versions, null, 2) + '\n');

console.log(`Validated and synchronized community release files for v${manifest.version}`);
