"""Browser host for the actual plugin UI and a temporary real HTTP kernel.

Only the Obsidian host and model responses are fixtures; production is untouched.
"""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = Path(os.environ.get('OPENCONTENT_PREVIEW_PLUGIN_DIR', ROOT / 'plugin')).resolve()
RUNTIME_DIR = os.environ.get('OPENCONTENT_PREVIEW_RUNTIME')


def start_fixture():
    helper = ROOT / 'tests/helpers/three_stage_http_bridge.py'
    command = [sys.executable, '-B', '-u', str(helper)]
    if RUNTIME_DIR:
        # Import the installed package before fixture helpers add the checkout to sys.path.
        bootstrap = ('import runpy,sys;sys.path.insert(0,sys.argv[1]);'
                     'import opencontent;'
                     'assert str(opencontent.__file__).startswith(sys.argv[1]);'
                     'runpy.run_path(sys.argv[2],run_name="__main__")')
        command = [sys.executable, '-B', '-u', '-c', bootstrap, str(Path(RUNTIME_DIR).resolve()), str(helper)]
    child = subprocess.Popen(command,
                             cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    line = child.stdout.readline()
    if not line:
        raise RuntimeError(child.stderr.read())
    return child, json.loads(line)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.dispatch()

    def do_POST(self):
        self.dispatch()

    def dispatch(self):
        if self.path == '/reset' and self.command == 'POST':
            self.server.child.communicate(input='\n', timeout=10)
            self.server.child, self.server.fixture = start_fixture()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{}')
            return
        if self.path == '/receipt' and self.command == 'POST':
            data = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
            out = ROOT / '.execution/ui-clarity-20261004'
            out.mkdir(parents=True, exist_ok=True)
            name = 'browser-e2e.json' if data['passed'] else 'browser-e2e-failure.json'
            (out / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{}')
            return
        if self.path.startswith('/api/'):
            route = self.path[4:]
            size = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(size) if size else None
            conn = http.client.HTTPConnection('127.0.0.1', self.server.fixture['port'], timeout=30)
            try:
                conn.request(self.command, route, raw, {'Authorization': 'Bearer ' + self.server.fixture['token'], 'Content-Type': 'application/json'})
                response = conn.getresponse()
                data = response.read()
                self.send_response(response.status)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(data)
            finally:
                conn.close()
            return
        files = {'/': (ROOT / 'tests/helpers/ui_clarity_preview.html', 'text/html; charset=utf-8'),
                 '/plugin.js': (PLUGIN_DIR / 'main.js', 'text/javascript; charset=utf-8'),
                 '/plugin-before.js': (ROOT / '.execution/ui-clarity-20261004/before/plugin/main.js', 'text/javascript; charset=utf-8'),
                 '/plugin.css': (PLUGIN_DIR / 'styles.css', 'text/css; charset=utf-8')}
        if self.path == '/fixture':
            screenshots = ROOT / '.execution/ui-clarity-20261004/browser'
            screenshots.mkdir(parents=True, exist_ok=True)
            data = json.dumps({**{k: v for k, v in self.server.fixture.items() if k not in ('port', 'token')},
                               'runtime': RUNTIME_DIR or str(ROOT), 'plugin_dir': str(PLUGIN_DIR),
                               'artifact_output': str(screenshots)}).encode()
            kind = 'application/json'
        elif self.path == '/before':
            data = (ROOT / 'tests/helpers/ui_clarity_preview.html').read_bytes().replace(b'src="/plugin.js"', b'src="/plugin-before.js"')
            kind = 'text/html; charset=utf-8'
        elif self.path in files:
            path, kind = files[self.path]
            data = path.read_bytes()
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)


def main():
    child, fixture = start_fixture()
    server = None
    try:
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.child, server.fixture = child, fixture
        print(json.dumps({'url': f'http://127.0.0.1:{server.server_port}', 'fixture_only': True}), flush=True)
        server.serve_forever()
    finally:
        (server.child if server else child).communicate(input='\n', timeout=10)


if __name__ == '__main__':
    main()
