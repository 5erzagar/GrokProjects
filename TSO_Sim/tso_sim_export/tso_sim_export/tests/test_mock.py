"""Runs the scraper against a local mock page (no internet needed). Run: python tests/test_mock.py"""
import functools, http.server, json, socketserver, sys, tempfile, threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import SimBrowser, save_results, export_zip

root = Path(__file__).parent / "mock_site"
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
class Q(handler.func):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Q, directory=str(root)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_address[1]}/index.html"

tmp = Path(tempfile.mkdtemp())
b = SimBrowser(tmp / "profile", headless=True)
print(b.call(b.open, url))
logs = []
camps = b.call(b.collect, 2, logs.append, 20)
print(json.dumps([(c["tab"], c["camp_id"], [(s["unit_total"], s["setup"]["attackers"][0]["general_id"]) for s in c["solutions"]]) for c in camps], ensure_ascii=False))
print("upload button clicked:", b.call(lambda: b._page().evaluate("!!window.__uploadClicked")))
assert b.call(lambda: b._page().evaluate("!!window.__uploadClicked")) is False
p = save_results(tmp / "out", "BountyHunterNew", camps)
m = b.call(b.save_map, tmp / "out", "BountyHunterNew")
d = b.call(b.debug_dump, tmp / "out")
n = export_zip(tmp / "out", tmp / "x.zip")
print(p.exists(), m, m.stat().st_size > 100, d.exists(), "zip files:", n)
assert len(camps) == 2 and camps[0]["camp_id"] == "48_2_17_86" and camps[1]["camp_id"] == "48_3_15_79"
# X = 2 distinct generals, cheapest winning army each. Knight 25 beats Cavalry 155 for the same general.
assert [s["unit_total"] for s in camps[0]["solutions"]] == [25, 230]
assert camps[0]["solutions"][1]["setup"]["attackers"][0]["general_name"] == "Ghost1"
assert [s["unit_total"] for s in camps[1]["solutions"]] == [25, 155]
assert p.parent == m.parent
b.call(b.close)
print("ALL OK", logs)
