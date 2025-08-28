import os
import pty
import select
import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext
import re

# --- ANSI parser (supports normal + bright colors and reset/bold) ---
SGR_RE = re.compile(r'\x1b\[(\d+(?:;\d+)*)m')

COLOR_MAP = {
    "30": "black", "31": "red", "32": "green", "33": "yellow",
    "34": "blue", "35": "magenta", "36": "cyan", "37": "white",
    "90": "br_black", "91": "br_red", "92": "br_green", "93": "br_yellow",
    "94": "br_blue", "95": "br_magenta", "96": "br_cyan", "97": "br_white",
}

def insert_with_ansi(widget, text):
    parts = SGR_RE.split(text)
    tags = []
    i = 0
    while i < len(parts):
        if i % 2 == 0:
            if parts[i]:
                widget.insert("end", parts[i], tags)
        else:
            codes = parts[i].split(";")
            if "0" in codes:  # reset
                tags = []
            for c in codes:
                if c == "1":  # bold
                    if "bold" not in tags:
                        tags.append("bold")
                elif c in COLOR_MAP:
                    tags = [t for t in tags if not t.startswith("fg_")]
                    tags.append("fg_" + COLOR_MAP[c])
        i += 1

def safe_insert(text):
    output_box.after(0, lambda: (insert_with_ansi(output_box, text), output_box.see("end")))

def run_holehe():
    email = email_entry.get().strip()
    if not email:
        output_box.insert("end", "⚠️ Please enter an email address.\n", ("fg_yellow",))
        return

    output_box.delete("1.0", "end")

    def worker():
        try:
            master_fd, slave_fd = pty.openpty()

            env = os.environ.copy()
            env["CLICOLOR"] = "1"
            env["CLICOLOR_FORCE"] = "1"
            env["FORCE_COLOR"] = "1"
            env["PY_COLORS"] = "1"

            proc = subprocess.Popen(
                ["holehe", email],
                stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
                env=env, close_fds=True, text=False
            )
            os.close(slave_fd)

            while True:
                r, _, _ = select.select([master_fd], [], [], 0.1)
                if master_fd in r:
                    try:
                        data = os.read(master_fd, 4096)
                    except OSError:
                        break
                    if not data:
                        break
                    safe_insert(data.decode("utf-8", errors="ignore"))

                if proc.poll() is not None:
                    while True:
                        r2, _, _ = select.select([master_fd], [], [], 0)
                        if master_fd in r2:
                            chunk = os.read(master_fd, 4096)
                            if not chunk:
                                break
                            safe_insert(chunk.decode("utf-8", errors="ignore"))
                        else:
                            break
                    break

            os.close(master_fd)
        except Exception as e:
            safe_insert(f"\n❌ Failed to run holehe: {e}\n")

    threading.Thread(target=worker, daemon=True).start()

# --- GUI ---
root = tk.Tk()
root.title("Holehe GUI (real terminal colors)")
root.geometry("400x400")

tk.Label(root, text="Enter Email:", font=("Arial", 12)).pack(pady=(10, 2))
email_entry = tk.Entry(root, width=50, font=("Arial", 12))
email_entry.pack(pady=2)
tk.Button(root, text="Check Email", command=run_holehe, font=("Arial", 12)).pack(pady=8)

output_box = scrolledtext.ScrolledText(
    root, wrap="word", width=100, height=30,
    font=("Consolas", 11),
    bg="black", fg="white", insertbackground="white"
)
output_box.pack(pady=10, fill="both", expand=True)

# tag styles
output_box.tag_configure("bold", font=("Consolas", 11, "bold"))
for name, color in {
    "black":"#000000", "red":"#ff4c4c", "green":"#3cd070", "yellow":"#ffcc33",
    "blue":"#4c9aff", "magenta":"#ff66ff", "cyan":"#00e5e5", "white":"#f2f2f2",
    "br_black":"#7f7f7f", "br_red":"#ff6b6b", "br_green":"#3ddc84",
    "br_yellow":"#ffd166", "br_blue":"#4dabf7", "br_magenta":"#f783ff",
    "br_cyan":"#66fff3", "br_white":"#ffffff",
}.items():
    output_box.tag_configure("fg_" + name, foreground=color)

root.mainloop()
