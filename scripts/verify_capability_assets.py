"""HTTP regression: capability assets must not poison core-object diagnostics."""
import argparse
import http.client
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import threading

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--runtime', type=Path, default=Path(__file__).resolve().parent.parent,
                        help='Kernel directory to verify, including an installed plugin kernel')
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    sys.path.insert(0, str(runtime))
    from opencontent.kernel import Kernel
    from opencontent.jobs import Jobs
    from opencontent.server import Server
    checks = {}
    scenario_error = None
    with tempfile.TemporaryDirectory(prefix='oc-assets-e2e-') as directory:
        kernel = Kernel(directory)
        jobs = Jobs(kernel)
        server = Server(kernel, jobs)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()

        def call(method, route, body=None):
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=20)
            try:
                conn.request(method, route, json.dumps(body).encode() if body is not None else None,
                             {'Authorization': 'Bearer ' + server.token, 'Content-Type': 'application/json'})
                response = conn.getresponse()
                result = json.loads(response.read())
                if response.status != 200:
                    raise RuntimeError((route, response.status, result))
                return result
            finally:
                conn.close()

        try:
            project = call('POST', '/projects', {'title': 'Fixture', 'goal': 'Asset isolation', 'audience': 'QA'})
            base = {'schema': 'opencontent.creative-task.v1', 'project': project['oc_id'],
                    'pack': 'narrative', 'profile': 'general-fiction'}
            raw = {'fixture': [{'title': 'Sample ' + str(i), 'rank': i, 'genre': 'fiction', 'words': 10,
                                'url': 'https://example.com/fixture/' + str(i),
                                'observed_at': '2026-09-26T00:00:00Z'}
                               for i in range(1, 4)]}
            chapters = [{'title': '合成第' + str(i) + '章',
                         'body': '这是一段合成软件验收故事。调查者发现错误档案，核对原始证据，澄清记录中的误解。' * 20}
                        for i in range(1, 4)]
            for task in ('long-scan', 'short-scan', 'long-analyze', 'short-analyze'):
                result = call('POST', '/capabilities/execute',
                              {**base, 'task': task, 'title': task, 'raw_data': raw,
                               'chapters': chapters, 'text': '\n\n'.join(chapter['body'] for chapter in chapters)})
                checks[task + '_succeeded'] = result['receipt']['status'] == 'SUCCEEDED'
                checks[task + '_board_clean'] = call('GET', '/board')['diagnostics'] == []
            checks['cards_readable'] = len(call('GET', '/capabilities/mechanisms')['mechanisms']) >= 3
            checks['project_readable'] = call('GET', '/objects/' + project['oc_id'])['object']['oc_id'] == project['oc_id']
            outside = Path(directory) / 'outside-vault'
            outside.mkdir()
            (outside / 'private-card.md').write_text('OUTSIDE_VAULT_CARD_SENTINEL', encoding='utf-8')
            link = kernel.vault.content / 'Deconstruction/Boundary/机制卡片'
            link.parent.mkdir(parents=True)
            if os.name == 'nt':
                subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(outside)],
                               check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                link.symlink_to(outside, target_is_directory=True)
            for method in ('GET', 'POST'):
                cards = call(method, '/capabilities/mechanisms', {} if method == 'POST' else None)['mechanisms']
                checks[method + '_rejects_linked_cards_outside_vault'] = all(
                    'OUTSIDE_VAULT_CARD_SENTINEL' not in card['content'] for card in cards)
            for relative in ('Project/broken.md', 'unexpected/broken.md'):
                path = kernel.vault.content / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('---\ntype: Invalid\n---\n', encoding='utf-8')
                checks[relative + '_diagnosed'] = any('OpenContent/' + relative in error
                                                     for error in call('GET', '/board')['diagnostics'])
            checks['http_scenario_completed'] = True
        except Exception as error:
            scenario_error = str(error)
            checks['http_scenario_completed'] = False
        finally:
            server.shutdown()
            server.server_close()
            jobs.close()
            worker.join()
    report = {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
              'runtime': str(runtime), 'server_module': str(sys.modules[Server.__module__].__file__),
              'error': scenario_error,
              'synthetic_fixture_only': True, 'native_obsidian_ui': 'UNVERIFIED'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
