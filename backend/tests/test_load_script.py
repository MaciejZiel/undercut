import importlib.util
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "perf" / "load_test.py"
spec = importlib.util.spec_from_file_location("load_test", SCRIPT)
load_test = importlib.util.module_from_spec(spec)
spec.loader.exec_module(load_test)


def test_percentile_picks_the_nearest_rank():
    values = [float(n) for n in range(1, 101)]
    assert load_test.percentile(values, 0.5) == 50
    assert load_test.percentile(values, 0.95) == 95
    assert load_test.percentile(values, 0.99) == 99
    assert load_test.percentile([], 0.95) == 0.0
    assert load_test.percentile([7.0], 0.95) == 7.0


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        status = 500 if self.path == "/boom" else 200
        self.send_response(status)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


def _run(paths):
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    results, lock = {"ms": [], "errors": 0}, threading.Lock()
    urls = [f"http://127.0.0.1:{server.server_port}{p}" for p in paths]
    deadline = load_test.time.monotonic() + 0.3
    load_test.worker(urls, deadline, {}, results, lock)
    server.shutdown()
    return results


def test_worker_records_latencies_and_errors_separately():
    ok = _run(["/fine"])
    assert ok["ms"] and ok["errors"] == 0
    mixed = _run(["/fine", "/boom"])
    assert mixed["ms"] and mixed["errors"] > 0
