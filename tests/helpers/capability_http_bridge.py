"""Node UI acceptance bridge; uses only a disposable Vault and local HTTP server."""
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from opencontent.kernel import Kernel
from opencontent.jobs import Jobs
from opencontent.server import Server

request = json.load(sys.stdin)
with tempfile.TemporaryDirectory() as directory:
    kernel = Kernel(directory)
    project = kernel.create_project('UI acceptance', 'Verify input', 'Tests')
    request['project'] = project['oc_id']
    providers = {}
    if request["task"] == "cover":
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from test_media_generation import ImageFixtureProvider
        providers["image-fixture"] = ImageFixtureProvider()
    server = Server(kernel, Jobs(kernel, providers))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port)
        connection.request('POST', '/capabilities/execute', json.dumps(request), {
            'Authorization': 'Bearer ' + server.token, 'Content-Type': 'application/json'})
        response = connection.getresponse()
        result = json.loads(response.read())
        if response.status == 200:
            if request['task'] == 'cover':
                assert result['mode'] == 'fixture'
                assert all(c['image']['decoded'] for c in result['candidates'])
                assert all((Path(directory)/c['path']).is_file() for c in result['candidates'])
            else:
                assert list(Path(directory).glob('OpenContent/Market/Long/*.md'))
                assert result['market_report']['total_samples'] == 3
        print(json.dumps({'status': response.status, 'data': result}))
        connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
