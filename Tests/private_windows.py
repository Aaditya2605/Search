#!/usr/bin/env python3
"""Private windows, in a hidden probe. Build first (`./build.sh`), then
`python3 Tests/private_windows.py`.

Its tabs are private and share one jar, which the normal window doesn't see;
no pins; never saved; closed, it's gone and ⇧⌘T doesn't bring it back.
The probe's folder goes to the Trash afterwards (no rm).
"""
import json, os, shutil, socket, subprocess, sys, threading, time
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

APP = str(Path(__file__).resolve().parents[1] / "build" / "Search.app")
W = f"private-windows-probe-{int(time.time())}"
HOME = os.path.expanduser("~")
SUPPORT = f"{HOME}/Library/Application Support/Search ({W})"
SUITE = f"com.officecommun.search.test.{W}"
SOCK = f"{SUPPORT}/bench.sock"

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        extra = [("Set-Cookie", "who=private; Path=/")] if self.path == "/set" else []
        body = f"<title>{self.path}</title><script>window.jar = document.cookie || 'none'</script>"
        self.send_response(200); self.send_header("Content-Type", "text/html")
        for k, v in extra: self.send_header(k, v)
        self.end_headers(); self.wfile.write(body.encode())
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_port}"

def cmd(req):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as c:
        c.settimeout(30); c.connect(SOCK); c.sendall(json.dumps(req).encode() + b"\n")
        data = b""
        while True:
            ch = c.recv(65536)
            if not ch: break
            data += ch
    a = json.loads(data.split(b"\n", 1)[0] or b"{}")
    if "error" in a: raise RuntimeError(f"{req}: {a['error']}")
    return a

def windows(action=None, **f):
    return cmd({"do": "windows", **({"action": action} if action else {}), **f})["windows"]

def tabs(n): return cmd({"do": "tabs", "window": n})["tabs"]
def jar(n, id):
    for _ in range(20):
        v = cmd({"do": "eval", "window": n, "id": id, "js": "window.jar"}).get("value")
        if v: return v
        time.sleep(0.3)

def trash(path):
    if not os.path.exists(path): return
    dest = f"{HOME}/.Trash/{os.path.basename(path)}.{int(time.time())}"
    shutil.move(path, dest)

passed = failed = 0
def ok(name, cond, extra=""):
    global passed, failed
    if cond: passed += 1; print("  ok  ", name)
    else: failed += 1; print("  FAIL", name, extra)

proc_before = set(subprocess.run(["pgrep", "-f", APP + "/Contents/MacOS"], capture_output=True, text=True).stdout.split())
try:
    for k in ["bench", "welcomed"]:
        subprocess.run(["defaults", "write", SUITE, k, "-bool", "true"])
    subprocess.run(["open", "-n", "-g", "-j", "--env", f"SEARCH_PROBE={W}", APP])
    for _ in range(150):
        if os.path.exists(SOCK): break
        time.sleep(0.1)
    time.sleep(2)

    # A pin in the normal window, which a private one must not show.
    windows("link", url=f"{BASE}/pinned"); time.sleep(1)
    first = tabs(1)[-1]["id"]
    cmd({"do": "pin", "window": 1, "id": first})

    ws = windows("private")
    ok("⇧⌘N opens a second window", len(ws) == 2, ws)
    ok("the second window is private", ws[-1]["private"] and not ws[0]["private"], ws)
    ok("the private window has no pins", ws[-1]["pins"] == [], ws[-1]["pins"])

    windows("front", n=2)
    windows("link", url=f"{BASE}/set"); time.sleep(1.5)
    windows("link", url=f"{BASE}/show"); time.sleep(1.5)
    pt = tabs(2)
    ok("every tab in the private window is private", pt and all(t["shy"] for t in pt), [(t["url"], t["shy"]) for t in pt])
    show = next((t for t in pt if t["url"].endswith("/show")), None)
    ok("a second private tab sees the first one's cookie (one jar)", show and jar(2, show["id"]) == "who=private",
       show and jar(2, show["id"]))

    windows("front", n=1)
    windows("link", url=f"{BASE}/show"); time.sleep(1.5)
    normal = next((t for t in tabs(1) if t["url"].endswith("/show")), None)
    ok("the normal window doesn't see the private cookie", normal and jar(1, normal["id"]) == "none",
       normal and jar(1, normal["id"]))
    ok("the normal window's tab isn't private", normal and not normal["shy"], normal)

    time.sleep(1.5)  # windows.json is written a moment after a change
    saved = json.load(open(f"{SUPPORT}/windows.json")) if os.path.exists(f"{SUPPORT}/windows.json") else []
    ok("the private window isn't saved", len(saved) <= 1, len(saved))

    ws = windows("close", n=2)
    ok("closed, the private window is gone", len(ws) == 1, ws)
    ok("nothing for ⇧⌘T to bring back", not cmd({"do": "windows"})["closedWindows"])
    ws = windows("reopen")
    ok("reopen brings back no window", len(ws) == 1, ws)
finally:
    try: cmd({"do": "quit"})
    except Exception: pass
    time.sleep(2)
    now = set(subprocess.run(["pgrep", "-f", APP + "/Contents/MacOS"], capture_output=True, text=True).stdout.split())
    for p in now - proc_before: subprocess.run(["kill", p])
    time.sleep(0.5)
    trash(SUPPORT)
    trash(f"{HOME}/Library/Preferences/{SUITE}.plist")
    print(f"{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
