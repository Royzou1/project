# main.py
import socket
import threading
import ast
import time

# ---------- Colored print helpers ----------
def print_server(msg: str):
    print(f"\033[92m[SERVER]\033[0m {msg}")  # green

def print_client(msg: str):
    print(f"\033[96m[CLIENT]\033[0m {msg}")  # cyan

# One lock for atomic prints (prevents interleaved lines)
print_lock = threading.Lock()

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
            print_server(f"OK: {code} from {addr}")
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
        # process on a thread so server stays responsive
        threading.Thread(target=handle_code, args=(msg, addr), daemon=True).start()

# ---------- Client (send-only) ----------
def start_client(message: str, host="127.0.0.1", port=9999, delay=0.2):
    time.sleep(delay)  # tiny delay so server is up in demos
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    with print_lock:
        c.sendto(message.encode("utf-8"), (host, port))
        print_client(f"Sent: {message}")
    c.close()  # done (no recv)

# ---------- Demo ----------
if __name__ == "__main__":
    # Start server in background
    threading.Thread(target=start_server, daemon=True).start()

    # Example sends (sequential; no client threads needed)
    start_client("3 + 5")
    start_client("hello")                       # rejected (bare literal)
    start_client("print('hello world')")        # valid
    start_client("for i in range(3) print(i)")  # syntax error (missing colon)
    time.sleep(1)