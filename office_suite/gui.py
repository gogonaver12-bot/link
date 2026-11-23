"""화면(tkinter). 기능 목록·입력칸은 플러그인 FIELDS 에서 자동 생성 → 새 기능 추가 시 화면 수정 불필요."""
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import VERSION, core

FONT = ("맑은 고딕", 12) if sys.platform == "win32" else ("TkDefaultFont", 12)
BIG = (FONT[0], 15, "bold")


def open_path(p):
    p = str(p)
    if sys.platform == "win32":
        os.startfile(p)  # noqa: S606 - 사용자가 누른 결과 파일/폴더 열기
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", p])


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"회사 도우미 v{VERSION}")
        self.geometry("1150x760")
        self.minsize(900, 600)
        self.option_add("*Font", FONT)
        st = ttk.Style(self)
        st.configure(".", font=FONT)
        st.configure("Menu.TButton", font=(FONT[0], 13), padding=10, anchor="w")
        st.configure("Run.TButton", font=BIG, padding=8)
        self.plugins, self.current, self.widgets, self.last_files = [], None, {}, []
        self._menu()
        left = ttk.Frame(self, padding=8)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="기능 선택", font=BIG).pack(anchor="w", pady=(0, 6))
        self.menu_box = ttk.Frame(left)
        self.menu_box.pack(fill="y")
        ttk.Separator(self, orient="vertical").pack(side="left", fill="y")
        right = ttk.Frame(self, padding=10)
        right.pack(side="left", fill="both", expand=True)
        self.h_name = ttk.Label(right, font=BIG)
        self.h_name.pack(anchor="w")
        self.h_desc = ttk.Label(right, foreground="#555", wraplength=820, justify="left")
        self.h_desc.pack(anchor="w", pady=(2, 8))
        # 스크롤 되는 입력칸 영역
        wrap = ttk.Frame(right)
        wrap.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(wrap, highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.form = ttk.Frame(self.canvas)
        self.form.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._win = self.canvas.create_window((0, 0), window=self.form, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-e.delta / 120), "units"))
        bar = ttk.Frame(right)
        bar.pack(fill="x", pady=6)
        self.run_btn = ttk.Button(bar, text="▶ 실행", style="Run.TButton", command=self.run)
        self.run_btn.pack(side="left")
        self.open_btn = ttk.Button(bar, text="결과 파일 열기", command=self.open_last, state="disabled")
        self.open_btn.pack(side="left", padx=6)
        ttk.Button(bar, text="결과 폴더", command=self.open_folder).pack(side="left")
        ttk.Button(bar, text="처음 값으로", command=lambda: self.select(self.current)).pack(side="left", padx=6)
        self.out = tk.Text(right, height=9, wrap="word", background="#F7F7F7", relief="flat")
        self.out.pack(fill="x")
        self.reload()

    def _menu(self):
        m = tk.Menu(self)
        h = tk.Menu(m, tearoff=0)
        h.add_command(label="기능 다시 불러오기 (새 기능 추가 후)", command=self.reload)
        h.add_command(label="새 기능 넣는 폴더 열기", command=self.open_plugins)
        h.add_command(label="결과물 폴더 열기", command=lambda: self.open_folder(root=True))
        h.add_separator()
        h.add_command(label="프로그램 정보", command=lambda: messagebox.showinfo(
            "회사 도우미", f"버전 {VERSION}\n저장 위치: {core.HOME}\n새 기능: {core.PLUGIN_DIR} 에 .py 파일 넣기"))
        m.add_cascade(label="도움말", menu=h)
        self.config(menu=m)

    def reload(self):
        for w in self.menu_box.winfo_children():
            w.destroy()
        self.plugins = core.load_plugins()
        for p in self.plugins:
            ttk.Button(self.menu_box, text=p.name + (" (오류)" if p.error else ""), width=24, style="Menu.TButton",
                       command=lambda p=p: self.select(p)).pack(fill="x", pady=2)
        keep = next((p for p in self.plugins if self.current and p.key == self.current.key), None)
        if self.plugins:
            self.select(keep or self.plugins[0])

    def select(self, p):
        if p is None:
            return
        self.current, self.widgets = p, {}
        for w in self.form.winfo_children():
            w.destroy()
        self.h_name.config(text=p.name)
        self.h_desc.config(text=p.error and f"불러오기 오류: {p.error}" or p.desc)
        pre = getattr(p.module, "defaults", lambda: {})() if p.module else {}
        self.form.columnconfigure(1, weight=1)
        for r, f in enumerate(p.fields):
            val = pre.get(f.key, f.default)
            ttk.Label(self.form, text=f.label).grid(row=r, column=0, sticky="nw", padx=(0, 10), pady=5)
            if f.kind == "multiline":
                w = tk.Text(self.form, height=9, wrap="none", undo=True)
                w.insert("1.0", str(val))
                get = lambda w=w: w.get("1.0", "end-1c")
            elif f.kind == "choice":
                var = tk.StringVar(value=str(val))
                w = ttk.Combobox(self.form, textvariable=var, values=list(f.choices), state="readonly")
                get = var.get
            elif f.kind == "check":
                var = tk.BooleanVar(value=bool(val))
                w = ttk.Checkbutton(self.form, variable=var)
                get = var.get
            else:
                var = tk.StringVar(value="" if val is None else (f"{val:g}" if isinstance(val, float) else str(val)))
                w = ttk.Entry(self.form, textvariable=var, show="*" if "key" in f.key else "")
                get = var.get
                if f.kind == "file":
                    ttk.Button(self.form, text="찾기", command=lambda var=var: var.set(
                        filedialog.askopenfilename() or var.get())).grid(row=r, column=2, padx=4)
            w.grid(row=r, column=1, sticky="we", pady=5)
            if f.help:
                ttk.Label(self.form, text=f.help, foreground="#888").grid(row=r, column=3, sticky="w", padx=6)
            self.widgets[f.key] = get
        self.canvas.yview_moveto(0)
        self._show("")

    def _show(self, text):
        self.out.config(state="normal")
        self.out.delete("1.0", "end")
        self.out.insert("1.0", text)
        self.out.config(state="disabled")

    def run(self):
        p = self.current
        raw = {k: get() for k, get in self.widgets.items()}
        self.run_btn.config(state="disabled", text="작업 중…")
        self._show("작업 중입니다. 잠시만 기다려 주세요…")

        box = []   # 작업 스레드는 화면을 직접 만지지 않고 결과만 넘김 (tkinter 스레드 안전)
        t = threading.Thread(target=lambda: box.append(core.run_plugin(p, raw)), daemon=True)
        t.start()

        def poll():
            if box:
                self._done(box[0])
            else:
                self.after(150, poll)
        self.after(150, poll)

    def _done(self, res):
        self.run_btn.config(state="normal", text="▶ 실행")
        self.last_files = res.files
        self.open_btn.config(state="normal" if res.files else "disabled")
        self._show(("✅ " if res.ok else "⚠ ") + res.message + ("\n\n저장: " + "\n".join(res.files) if res.files else ""))

    def open_last(self):
        if self.last_files:
            open_path(self.last_files[0])

    def open_folder(self, root=False):
        d = core.OUT if root or not self.current else core.OUT / self.current.key
        d.mkdir(parents=True, exist_ok=True)
        open_path(d)

    def open_plugins(self):
        core.PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
        open_path(core.PLUGIN_DIR)


def main():
    App().mainloop()
