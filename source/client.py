# client.py
import socket
import time
import argparse

def send_udp(message: str, host="127.0.0.1", port=9999, delay=0.0):
    if delay:
        time.sleep(delay)
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        c.sendto(message.encode("utf-8"), (host, port))
        print(f"\033[96m[CLIENT]\033[0m Sent: {message}")
    finally:
        c.close()

# ---------- Snippet factory (dispatch by 'string') ----------
def make_code(name: str, *, extra: str | None = None) -> str:
    table = {
        "hello": lambda: "print('hello world')",
        "loop":  lambda: "for i in range(3):\n\tprint(i)\n\tsleep(1)",
        "sum10": lambda: "print(sum(range(1, 11)))",
        "bad":   lambda: "hello",  # will be rejected by server validator
        "while":  lambda: "while True:\n\tpass",  # tight CPU loop, no sleep
    }
    if name in table:
        return table[name]()
    # Fallback modes:
    # 1) If name starts with 'code:', treat the rest as raw python to send.
    if name.startswith("code:"):
        return name[len("code:"):]
    # 2) If 'extra' is provided, emit a tiny program using both.
    if extra is not None:
        return f"print({name!r} + ' ' + {extra!r})"
    # 3) Otherwise just send 'name' as-is (likely rejected by validator).
    return name

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="UDP client that picks a code snippet by 'string'.")
    ap.add_argument("string", help="Selector for the snippet (e.g., hello, loop, sum10, bad, or 'code:<python>')")
    ap.add_argument("--extra", help="Optional extra string some snippets use", default=None)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9999)
    ap.add_argument("--delay", type=float, default=0.0, help="Optional delay before send")
    args = ap.parse_args()

    code = make_code(args.string, extra=args.extra)
    send_udp(code, host=args.host, port=args.port, delay=args.delay)
