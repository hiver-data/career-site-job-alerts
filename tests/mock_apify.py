"""Mock Apify API for tests. Serves rows from tests/rows.json (one page per call, in order).

Rows are real items returned by cloud runs of hiver/career-site-job-search 0.6.7
(runs g0j0pBAXsMqwHoYKY, KJNQ7dbMjkTa6WhYo, IYYeoxWbvWu4cxhcv, rTAZr8eHkz0jcPZU1).
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PAGES = json.load(open(sys.argv[2]))["pages"]
calls = {"n": 0}


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path.startswith("/v2/acts/hiver~career-site-job-search/run-sync-get-dataset-items"):
            assert "token=" in self.path
            sent = json.loads(body)
            assert sent["keywords"] and sent["maxJobs"] == 20, sent
            out = PAGES[min(calls["n"], len(PAGES) - 1)]
            calls["n"] += 1
            self._send(200, out)
        elif self.path.startswith("/hook"):
            open(sys.argv[3], "ab").write(body + b"\n")
            self._send(200, {"ok": True})
        else:
            self._send(404, {})

    def _send(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
