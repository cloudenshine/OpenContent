import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from .vault import Problem
from . import lifecycle
from . import discovery, workbench, ideation
from .publishing import Publishing
from .providers import detect_cli, activate_cli
from .model_discovery import discover_available_models


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, kernel, jobs, port=0):
        self.kernel, self.jobs = kernel, jobs
        self.publishing = Publishing(kernel)
        self.token = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, status, data):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def dispatch(self):
        self.connection.settimeout(10)
        body = None
        if self.command == "POST":
            if self.headers.get("Transfer-Encoding"):
                raise Problem("Transfer encoding is not supported", 400)
            try:
                size = int(self.headers.get("Content-Length", "-1"))
            except ValueError:
                raise Problem("Invalid content length", 400)
            if not 0 <= size <= 1_000_000:
                raise Problem("Request body must be between 0 and 1 MB", 413)
            raw = self.rfile.read(size)
            if self.headers.get_content_type() != "application/json":
                raise Problem("JSON required", 415)
            try:
                body = json.loads(raw)
            except (json.JSONDecodeError, UnicodeError):
                raise Problem("Malformed JSON", 400)
            if not isinstance(body, dict):
                raise Problem("JSON object required", 400)
        expected_host = "127.0.0.1:" + str(self.server.server_port)
        if self.headers.get("Host") != expected_host:
            raise Problem("Invalid loopback Host", 403)
        # Electron requestUrl normally has no Origin; ordinary browser pages are refused.
        if self.headers.get("Origin") or self.headers.get("Sec-Fetch-Site") in ("cross-site", "same-site"):
            raise Problem("Browser origins cannot control this kernel", 403)
        authorization = self.headers.get("Authorization", "")
        if not secrets.compare_digest(authorization, "Bearer " + self.server.token):
            raise Problem("Kernel authentication required", 401)
        route = urlsplit(self.path).path
        k, jobs = self.server.kernel, self.server.jobs
        pub = self.server.publishing
        if self.command == "GET":
            if route == '/ideation/scope': return ideation.scope(k)
            if route == '/models':
                cli = list(jobs.providers.keys())[0] if jobs.providers else 'codex'
                current_model = getattr(list(jobs.providers.values())[0], 'model', None) if jobs.providers else None
                return {'cli': cli, 'current': current_model, 'models': discover_available_models(cli)}
            if route == '/providers': return {'available':detect_cli(),'active':{n:p.capabilities() for n,p in jobs.providers.items()},'notice':getattr(jobs,'provider_notice',None) if not jobs.providers else None}
            if route == '/sources': return lifecycle.library(k)
            if route == '/publications': return pub.list()
            if route == "/health":
                return {"version": "0.8.0", "vault": str(k.vault.root), "providers": {name: p.capabilities() for name, p in jobs.providers.items()}}
            if route == "/board":
                return {**k.board(), "jobs": jobs.list()}
            if route.startswith("/objects/"):
                return k.inspect(route.split("/")[-1])
            if route == "/jobs":
                return jobs.list()
        elif self.command == "POST":
            if route == '/ideation/preview': return ideation.preview(k,body.get('direction',''),body.get('folders'),body.get('limit',24))
            if route == '/ideation/retry': return jobs.retry_ideation(body['id'])
            if route == '/ideation/start': return jobs.discover(body['preview'],body.get('provider'))
            if route == '/ideation/status': return ideation.status(k,body['id'])
            if route == '/ideation/create': return ideation.create(k,body['run'],body['idea'])
            if route == '/providers/activate': return activate_cli(jobs,body['name'],model=body.get('model'))
            if route == '/discovery': return ideation.preview(k,body.get('goal','')) if body.get('ideas') else discovery.recommend(k,body.get('goal',''))
            if route == '/projects/selected': return discovery.create_selected(k,body['title'],body['goal'],body['audience'],body.get('selected',[]),body['token'])
            if route == '/conversation/history': return {'turns':workbench.history(k,body['project']),'token':k.vault.token()}
            if route == '/conversation/send': return jobs.submit(body['project'],body.get('provider'),expected=body['token'],instruction=body['instruction'],mode=body.get('mode','discuss'))
            if route == '/conversation/apply': return workbench.apply_revision(k,body['project'],body['turn'],body['token'])
            if route == '/sources/preview': return lifecycle.refresh_preview(k,body['material'])
            if route == '/sources/refresh': return lifecycle.refresh_source(k,body['material'],body['body'],body['source_hash'],body['token'])
            if route == '/sources/reuse': return lifecycle.reuse_material(k,body['material'],body['project'],body['token'])
            if route == '/projects/plan': return lifecycle.plan_project(k,body['project'],body['planned_for'],body['token'])
            if route == '/channels': return pub.configure(body['name'],body['appid'],body.get('secret',''),body.get('secret_env',''),body.get('channel_id'),body.get('publish_mode'))
            if route == '/channels/check':
                adapter=pub.adapter(body['channel']);adapter.token()
                return {'status':'TOKEN_OK','identity':adapter.identity(),'note':'令牌可用不代表具有草稿或发表权限；实际操作仍受微信权限限制。'}
            if route == '/channels/cover': return pub.upload_cover(body['channel'],body['path'])
            if route == '/publications/prepare': return pub.prepare(body['artifact'],body['channel'],body['action'],body['token'],body.get('options'),body.get('draft_publication'))
            if route == '/publications/confirm': return pub.confirm(body['publication'],body['confirmation'],body['reviewer'],body['token'])
            if route == '/publications/reconcile': return pub.reconcile(body['publication'],body.get('recovery_id'))
            if route == '/publications/cancel': return pub.cancel_preview(body['publication'],body['token'])
            if route == '/feedback': return lifecycle.feedback(k,body['publication'],body['source'],body['body'],body['suggestion'],body['token'])
            if route == '/feedback/decide': return lifecycle.judge_feedback(k,body['publication'],body['feedback'],body['decision'],body['reviewer'],body['reason'],body['token'])
            if route == '/feedback/project': return lifecycle.next_project(k,body['publication'],body['feedback'],body['title'],body['goal'],body['audience'],body['token'])
            if route == "/projects":
                return k.create_project(body["title"], body["goal"], body["audience"])
            if route == "/objects":
                return k.add(body["project"], body["type"], body["title"], body["body"], body.get("fields", {}), body["token"])
            if route == "/capture":
                return k.capture(body["project"], body["title"], body["body"], body["source"], body["token"], body.get("source_url"))
            if route == "/handoff":
                return k.handoff(body["artifact"], body["token"])
            if route == "/advance":
                return k.advance(body["project"], body["target"], body["token"], body.get("thesis"))
            if route == "/reviews":
                return k.review(body["artifact"], body["reviewer"], body["axes"], body["claims_complete"],
                                body.get("conflict_resolution", ""), body.get("summary", ""), body["token"])
            if route == "/decisions":
                return k.decide(body["artifact"], body["decision"], body["reviewer"], body["reason"], body["token"])
            if route == "/jobs":
                return jobs.submit(body["project"], body.get("provider"), body.get("stage"), body.get("resume"), body.get("token"))
            if route == "/cancel":
                return jobs.cancel(body["id"])
            if route == "/shutdown":
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return {"status": "stopping"}
        raise Problem("Unknown endpoint", 404)

    def do_GET(self):
        try:
            self.respond(200, self.dispatch())
        except Problem as e:
            self.respond(e.status, {"error": str(e)})
        except (KeyError, TypeError, ValueError) as e:
            self.respond(422, {"error": "Invalid request or Markdown schema: " + str(e)})
        except OSError as e:
            self.respond(503, {"error": "Local IO failure: " + str(e)})
        except Exception as e:
            self.respond(500, {"error": type(e).__name__ + ": " + str(e)})

    do_POST = do_GET
