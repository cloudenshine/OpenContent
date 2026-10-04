"""Run unchanged Windows regressions with real link fixtures and durable evidence."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    'test_capability_runtime_acceptance.RuntimeAcceptanceTests.test_output_path_rejects_internal_symlinks_and_windows_forms',
    'test_market_sources.MarketSourceTests.test_import_rejects_symlink_hardlink_and_nonregular_file',
    'test_media_generation.CoverGenerationTests.test_linked_images_and_lexical_ancestor_links_fail',
)


def source_hashes():
    paths = [p for directory in ('opencontent', 'plugin', 'tests', 'scripts', 'packs', 'templates')
             for p in (ROOT / directory).rglob('*')
             if p.is_file() and '__pycache__' not in p.parts]
    paths += [ROOT / 'docs/verification.json', ROOT / 'package.json']
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.exists()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / '.execution').resolve()):
        parser.error('Evidence output must be inside repository .execution')
    if output.exists():
        parser.error('Evidence directory already exists; use a fresh output directory')
    output.mkdir(parents=True)
    os.chdir(ROOT)
    report = {'schema': 'opencontent.windows-verification.v1', 'status': 'FAIL',
              'at': datetime.now(timezone.utc).isoformat(), 'python': sys.executable,
              'python_version': sys.version, 'checks': [], 'source_hashes_before': source_hashes(),
              'persistent_permission_changes': False}

    def run(name, command):
        test_path = os.pathsep.join((str(ROOT / 'tests'), str(ROOT), os.environ.get('PYTHONPATH', '')))
        result = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHON': sys.executable, 'PYTHONPATH': test_path},
                                capture_output=True, text=True, encoding='utf-8', errors='replace')
        raw = (result.stdout + result.stderr).encode('utf-8')
        log = output / (name + '.log')
        log.write_bytes(raw)
        check = {'name': name, 'command': command, 'exit_code': result.returncode,
                 'log': log.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(raw).hexdigest()}
        report['checks'].append(check)
        print(('PASS ' if result.returncode == 0 else 'FAIL ') + name, flush=True)
        return check, raw.decode('utf-8')

    try:
        package_bytes = (ROOT / 'package.json').read_bytes()
        if hashlib.sha256(package_bytes).hexdigest() != report['source_hashes_before']['package.json']:
            raise RuntimeError('Node manifest changed while capturing the initial test command')
        node_command = json.loads(package_bytes)['scripts']['test'].split()
        if os.name != 'nt':
            raise RuntimeError('This entry point verifies native Windows only')
        run('token-privileges', ['whoami', '/priv'])
        import ctypes
        report['elevated_admin'] = bool(ctypes.windll.shell32.IsUserAnAdmin())
        with tempfile.TemporaryDirectory(prefix='oc-real-windows-links-') as temporary:
            base = Path(temporary)
            source = base / 'source.txt'
            source.write_text('synthetic link fixture', encoding='utf-8')
            real = base / 'real'
            real.mkdir()
            file_link, directory_link, hardlink = (base / n for n in ('file-link', 'directory-link', 'hardlink'))
            file_link.symlink_to(source)
            directory_link.symlink_to(real, target_is_directory=True)
            os.link(source, hardlink)
            report['real_link_preflight'] = {
                'file_symlink': file_link.is_symlink() and file_link.resolve() == source,
                'directory_symlink': directory_link.is_symlink() and directory_link.resolve() == real,
                'hardlink': os.path.samefile(source, hardlink) and source.stat().st_nlink == 2,
                'file_reparse_tag': file_link.lstat().st_reparse_tag,
                'directory_reparse_tag': directory_link.lstat().st_reparse_tag,
                'fixtures_removed_after_probe': True,
            }
            if not all(report['real_link_preflight'][key] for key in ('file_symlink', 'directory_symlink', 'hardlink')):
                raise RuntimeError('Real link fixtures were not recognized')
        sys.path.insert(0, str(ROOT / 'tests'))
        sys.path.insert(0, str(ROOT))
        targeted, targeted_text = run('targeted-three', [sys.executable, '-B', '-m', 'unittest', '-v', *TARGETS])
        targeted['executions'] = int(re.search(r'Ran (\d+) tests?', targeted_text)[1])
        if targeted['exit_code'] or targeted['executions'] != 3 or 'skipped=' in targeted_text:
            raise RuntimeError('The original three assertions did not all pass')
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
        def flatten(tests):
            return [identifier for test in tests for identifier in
                    (flatten(test) if isinstance(test, unittest.TestSuite) else [test.id()])]
        inventory = flatten(suite)
        (output / 'test-inventory.json').write_text(json.dumps(inventory, indent=2), encoding='utf-8')
        if not inventory or any('unittest.loader._FailedTest.' in identifier for identifier in inventory):
            raise RuntimeError('Unable to discover the complete test inventory')
        full, full_text = run('python-full', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'])
        match = re.search(r'Ran (\d+) tests?', full_text)
        # unittest prints a docstring on the next line for four existing tests.
        executed_ids = re.findall(r'^\w+ \(([^)]+)\)(?= \.\.\. |\r?$)', full_text, re.MULTILINE)
        (output / 'executed-test-inventory.json').write_text(json.dumps(executed_ids, indent=2), encoding='utf-8')
        discovered_counts, executed_counts = Counter(inventory), Counter(executed_ids)
        full.update(executions=int(match[1]) if match else None, discovered=len(inventory),
                    unique_tests=len(set(inventory)), skipped=int(re.search(r'skipped=(\d+)', full_text)[1])
                    if re.search(r'skipped=(\d+)', full_text) else 0,
                    identities_matched=discovered_counts == executed_counts,
                    missing_test_executions=list((discovered_counts - executed_counts).elements()),
                    unexpected_test_executions=list((executed_counts - discovered_counts).elements()))
        if full['executions'] != len(inventory) or full['skipped'] or not full['identities_matched']:
            raise RuntimeError('Full inventory was not executed without skips')
        # Keep the same Node test list as package.json; avoid npm's Windows .cmd shell handling.
        node, node_text = run('node-full', node_command)
        for key in ('tests', 'pass', 'fail', 'skipped'):
            match = re.search(r'(?:ℹ |# )' + key + r' (\d+)', node_text)
            node[key] = int(match[1]) if match else None
        if node['tests'] is None or node['skipped'] != 0:
            raise RuntimeError('Node inventory was not executed without skips')
        run('capability-http', [sys.executable, '-B', 'scripts/verify_capability_assets.py',
                               '--runtime', '.', '--output', str(output / 'capability-http.json')])
    except Exception as error:
        report['error'] = str(error)
        if isinstance(error, OSError) and getattr(error, 'winerror', None) == 1314:
            report['status'] = 'BLOCKED'
            report['remedy'] = 'Run scripts/verify_windows.ps1 -Elevate and approve the standard Windows UAC prompt.'
        print(report['status'] + ': ' + str(error), flush=True)
    finally:
        after = source_hashes()
        before = report['source_hashes_before']
        report['changed_during_checks'] = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
        if 'error' not in report and not report['changed_during_checks'] and all(
                check['exit_code'] == 0 for check in report['checks']):
            report['status'] = 'PASS'
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(str(output / 'report.json'), flush=True)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
