# server.py
import socket
import threading
import ast
import time
import sys
from types import MappingProxyType

# ---------- Minimal safe builtins (no __import__) ----------
SAFE_BUILTINS = MappingProxyType({
    "sleep": time.sleep,
    "print": print,
    "range": range,
    "len": len,
    "min": min,
    "max": max,
    "sum": sum,
    "enumerate": enumerate,
})

# One lock for atomic prints (prevents interleaved lines)
print_lock = threading.Lock()

def print_server(msg: str):
    print(f"\033[92m[SERVER]\033[0m {msg}")  # green

# ---------- Time limit tracer ----------
def _time_tracer(seconds: float):
    deadline = time.time() + seconds
    def tracer(frame, event, arg):
        if time.time() > deadline:
            raise TimeoutError("Time limit exceeded")
        return tracer
    return tracer

# ---------- Exec sandbox (per thread) ----------
def _exec_in_thread(code: str, addr, time_limit_sec: float = 12.0):
    """
    Executes untrusted code in THIS thread with:
      - tiny builtin whitelist
      - per-thread time limit (sys.settrace)
    """
    sys.settrace(_time_tracer(time_limit_sec))
    g = {"__builtins__": SAFE_BUILTINS}
    l = {}
    try:
        compiled = compile(code, "<socket_input>", "exec")
        exec(compiled, g, l)
        with print_lock:
            print_server(f"RAN (≤{time_limit_sec}s): {code} from {addr}")
    except TimeoutError as e:
        with print_lock:
            print_server(f"TIMEOUT: {e} for {addr} (code: {code})")
    except BaseException as e:
        with print_lock:
            print_server(f"RUNTIME ERROR: {e} for {addr} (code: {code})")
    finally:
        sys.settrace(None)

# ---------- Validation ----------
def is_meaningful_python(code: str):
    """
    Raise SyntaxError for a bare literal/name (e.g., "hello" or foo).
    Otherwise compile() to ensure syntax is valid.
    """
    tree = ast.parse(code, mode='exec')
    if (len(tree.body) == 1
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, (ast.Constant, ast.Name))):
        raise SyntaxError("Bare literal/name is not allowed")
    compile(code, "<socket_input>", "exec")

# ---------- Server (receive-only) ----------
def handle_code(code: str, addr):
    try:
        is_meaningful_python(code)
        with print_lock:
            t = threading.Thread(
                target=_exec_in_thread,
                args=(code, addr),
                kwargs={"time_limit_sec": 60.0},
                daemon=True,
            )
            t.start()
            print_server(f"OK -> spawned thread {t.name} for {addr}")

    except Exception as e:
        with print_lock:
            print_server(f"ERROR: {e} from {addr}")

def start_server(host="127.0.0.1", port=9999):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    with print_lock:
        print_server(f"Listening on {host}:{port}")

    while True:
        data, addr = sock.recvfrom(65535)
        msg = data.decode("utf-8", errors="ignore").strip()
        if not msg:
            continue
        threading.Thread(target=handle_code, args=(msg, addr), daemon=True).start()

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="UDP exec server")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=9999)
    args = p.parse_args()
    start_server(args.host, args.port)
