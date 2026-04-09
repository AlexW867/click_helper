import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import copy
import uuid
import subprocess
import pyautogui
from typing import List, Optional
from pynput import keyboard
import os
import sys
from models import ClickAction, SleepAction, LoopAction, serialize_actions, deserialize_actions
from recorder import Recorder
from player import Player

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Platform-specific font settings
if sys.platform == 'darwin':
    FONT_UI = "PingFang TC"
    FONT_MONO = "Helvetica Neue"
else:
    FONT_UI = "Microsoft JhengHei"
    FONT_MONO = "Segoe UI"

class ClickMasterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Click 小幫手")
        self.root.geometry("1150x850")
        
        # Set window icon (supports bundled EXE)
        try:
            icon_path = resource_path("click_helper.ico")
            self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Could not load icon: {e}")
        
        self.actions: List = []
        self.recording = False
        self._caffeinate_proc = None
        self.recorder = Recorder(self.add_action, self.stop_recording_ui)
        self.player = None
        
        # Global Hotkey for F10 (Toggle Recording)
        self.hotkey_listener = keyboard.Listener(on_press=self.on_global_keypress)
        self.hotkey_listener.start()
        
        self.dragging_node = None
        self.resizing_node = None
        self.connecting_node = None
        self.selected_node = None
        self.temp_line = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        self.setup_styles()
        self.setup_ui()
        self.update_coords_loop()
        
        # Prevent sleep while the app is running
        self.set_sleep_prevention(True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def setup_styles(self):
        self.colors = {
            "bg": "#ffffff", "toolbar": "#f1f3f5", "grid": "#f8f9fa",
            "loop": "#f3f0ff", "click": "#e7f5ff", "sleep": "#fff4e6",
            "port": "#4dabf7", "handle": "#ced4da", "outline": "#adb5bd",
            "comment": "#000000"
        }
        self.style = ttk.Style()
        self.style.configure("Toolbar.TFrame", background=self.colors["toolbar"])
        self.style.configure("TLabel", background=self.colors["toolbar"], font=(FONT_UI, 10))
        self.style.configure("Group.TLabel", background=self.colors["toolbar"], font=(FONT_UI, 9, "bold"), foreground="#495057")
        self.style.configure("TButton", font=(FONT_UI, 10))

    def setup_ui(self):
        # Toolbar
        self.toolbar = ttk.Frame(self.root, padding="5", style="Toolbar.TFrame")
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        
        # Group 1: 工作 (Work)
        ttk.Label(self.toolbar, text=" 工作 ", style="Group.TLabel").pack(side=tk.LEFT, padx=2)
        self.rec_btn = ttk.Button(self.toolbar, text="錄製 (F10)", command=self.toggle_recording)
        self.rec_btn.pack(side=tk.LEFT, padx=5)
        
        self.play_btn = ttk.Button(self.toolbar, text="執行", command=self.play_sequence)
        self.play_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(self.toolbar, text="清除", command=self.clear_actions).pack(side=tk.LEFT, padx=5)
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        
        # Group 2: 新增 (Add)
        ttk.Label(self.toolbar, text=" 新增 ", style="Group.TLabel").pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="點擊", command=lambda: self.add_click_at(400, 100)).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="等待", command=lambda: self.add_sleep_at(400, 200)).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="迴圈", command=lambda: self.add_loop_dialog(400, 300)).pack(side=tk.LEFT, padx=2)
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        
        # Group 3: 備份 (Backup)
        ttk.Label(self.toolbar, text=" 備份 ", style="Group.TLabel").pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="匯入", command=self.import_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="匯出", command=self.export_file).pack(side=tk.LEFT, padx=2)
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        
        # Group 4: 說明 (About)
        ttk.Label(self.toolbar, text=" 說明 ", style="Group.TLabel").pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="關於", command=self.show_about).pack(side=tk.LEFT, padx=2)

        self.status_var = tk.StringVar(value="準備就緒")
        ttk.Label(self.toolbar, textvariable=self.status_var).pack(side=tk.RIGHT, padx=10)
        
        # Canvas
        self.canvas = tk.Canvas(self.root, bg=self.colors["bg"], highlightthickness=0)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.draw_grid()
        
        # Status Bar (Bottom)
        self.footer = ttk.Frame(self.root, padding="2", style="Toolbar.TFrame")
        self.footer.pack(side=tk.BOTTOM, fill=tk.X)
        self.coord_var = tk.StringVar(value="螢幕座標 - X: 0, Y: 0")
        ttk.Label(self.footer, textvariable=self.coord_var, font=(FONT_MONO, 9)).pack(side=tk.LEFT, padx=10)
        ttk.Label(self.footer, text="by AlexW", font=(FONT_MONO, 9, "italic"), foreground="#868e96").pack(side=tk.RIGHT, padx=10)
        
        # Bindings
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.root.bind("<Delete>", self.on_delete_key)

    def draw_grid(self):
        for i in range(0, 3000, 100):
            self.canvas.create_line(i, 0, i, 3000, fill=self.colors["grid"], tags="grid")
            self.canvas.create_line(0, i, 3000, i, fill=self.colors["grid"], tags="grid")

    def update_coords_loop(self):
        x, y = pyautogui.position()
        self.coord_var.set(f"螢幕座標 - X: {int(x)}, Y: {int(y)}")
        self.root.after(50, self.update_coords_loop)

    def on_global_keypress(self, key):
        if key == keyboard.Key.f10:
            self.root.after(0, self.toggle_recording)
        elif key == keyboard.Key.f11:
            if self.player:
                self.player.request_stop()

    def toggle_recording(self):
        if not self.recording:
            self.recording = True
            self.rec_btn.config(text="停止錄製 (F10)")
            self.root.iconify(); time.sleep(0.5); self.recorder.start()
            self.status_var.set("正在錄製... (按下 F10 停止)")
        else:
            self.recorder.stop()

    def add_action(self, action):
        flat = self.get_flat_sequence(self.actions)
        n = len(flat)
        action.ui_x, action.ui_y = 50 + (n % 4) * 250, 50 + (n // 4) * 180
        if not action.comment: action.comment = str(n + 1)
        self.actions.append(action); self.refresh_editor()
        
    def stop_recording_ui(self):
        self.recording = False
        self.rec_btn.config(text="錄製 (F10)")
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.root.attributes("-topmost", True)
        self.root.attributes("-topmost", False)
        self.status_var.set("準備就緒")
        self.refresh_editor()

    def refresh_editor(self):
        self.canvas.delete("node", "line")
        self.render_by_layer(self.actions, is_bg=True)
        self.draw_connections()
        self.render_by_layer(self.actions, is_bg=False)

    def render_by_layer(self, actions, is_bg=True):
        for a in actions:
            if isinstance(a, LoopAction):
                if is_bg: self.draw_node_frame(a)
                self.render_by_layer(a.children, is_bg)
            else:
                if is_bg: self.draw_node_frame(a)
                else: self.draw_node_content(a)
        if not is_bg:
            for a in actions:
                if isinstance(a, LoopAction): self.draw_node_content(a)

    def draw_node_frame(self, a):
        tag = f"obj_{a.uid}"
        outline = "#339af0" if self.selected_node == a else self.colors["outline"]
        bg = self.colors["loop"] if isinstance(a, LoopAction) else \
             self.colors["click"] if isinstance(a, ClickAction) else self.colors["sleep"]
        stipple = "gray25" if isinstance(a, LoopAction) else ""
        self.canvas.create_rectangle(a.ui_x, a.ui_y, a.ui_x+a.ui_w, a.ui_y+a.ui_h, 
                                   fill=bg, outline=outline, width=2 if self.selected_node == a else 1, 
                                   tags=("node", tag, "body"), stipple=stipple)
        self.canvas.create_rectangle(a.ui_x+a.ui_w-12, a.ui_y+a.ui_h-12, a.ui_x+a.ui_w, a.ui_y+a.ui_h, 
                                   fill=self.colors["handle"], outline="#fff", tags=("node", tag, "handle"))

    def draw_node_content(self, a):
        tag = f"obj_{a.uid}"; x, y, w, h = a.ui_x, a.ui_y, a.ui_w, a.ui_h
        if a.comment:
            self.canvas.create_text(x+5, y+5, text=a.comment, anchor="nw", width=w-10,
                                   font=(FONT_UI, 11, "bold"), fill=self.colors["comment"], tags=("node", tag))
            offset_y = 28
        else:
            offset_y = 5
        self.canvas.create_oval(x+w-6, y+h/2-6, x+w+6, y+h/2+6, fill=self.colors["port"], outline="#fff", tags=("node", tag, "port", "out_port"))
        if isinstance(a, ClickAction):
            header = f"{'左鍵' if a.button=='left' else '右鍵'}: {a.x}, {a.y}"
            self.canvas.create_text(x+10, y+offset_y, text=header, anchor="nw", font=(FONT_UI, 10, "bold"), tags=("node", tag))
            self.canvas.create_text(x+10, y+offset_y+22, text=f"點擊後等待: {a.delay}s", anchor="nw", font=(FONT_UI, 9), tags=("node", tag))
        elif isinstance(a, SleepAction):
            self.canvas.create_text(x+10, y+offset_y, text="等待", anchor="nw", font=(FONT_UI, 10, "bold"), tags=("node", tag))
            self.canvas.create_text(x+10, y+offset_y+22, text=f"秒數: {a.seconds}s", anchor="nw", font=(FONT_UI, 9), tags=("node", tag))
        elif isinstance(a, LoopAction):
            self.canvas.create_text(x+10, y+offset_y, text="迴圈", anchor="nw", font=(FONT_UI, 10, "bold"), tags=("node", tag))
            self.canvas.create_text(x+10, y+offset_y+22, text=f"重複次數: {a.count}", anchor="nw", font=(FONT_UI, 9), tags=("node", tag))

    def draw_connections(self):
        flat = self.get_flat_sequence(self.actions)
        uid_map = {a.uid: a for a in flat}
        for a in flat:
            if a.next_id and a.next_id in uid_map:
                a2 = uid_map[a.next_id]
                x1, y1 = a.ui_x + a.ui_w + 5, a.ui_y + a.ui_h / 2
                x2, y2 = a2.ui_x - 5, a2.ui_y + a2.ui_h / 2
                mid_x = x1 + (x2 - x1) / 2
                self.canvas.create_line(x1, y1, mid_x, y1, mid_x, y2, x2, y2, 
                                       arrow=tk.LAST, fill="#adb5bd", width=2, tags="line", joinstyle=tk.MITER)

    def get_flat_sequence(self, actions):
        res = []
        for a in actions:
            res.append(a); 
            if isinstance(a, LoopAction): res.extend(self.get_flat_sequence(a.children))
        return res

    def on_left_click(self, event):
        items = self.canvas.find_overlapping(event.x-3, event.y-3, event.x+3, event.y+3)
        target_item = None
        for item in reversed(items):
            if "port" in self.canvas.gettags(item):
                target_item = item; break
        if not target_item:
            for item in reversed(items):
                if "node" in self.canvas.gettags(item):
                    target_item = item; break
        if target_item:
            tags = self.canvas.gettags(target_item)
            uid = next((t.split("_")[1] for t in tags if t.startswith("obj_")), None)
            if uid:
                node = self.find_by_uid(uid, self.actions); self.selected_node = node
                if "out_port" in tags:
                    self.connecting_node = node
                    self.temp_line = self.canvas.create_line(event.x, event.y, event.x, event.y, dash=(3,3), fill="#adb5bd", tags="temp")
                elif "handle" in tags: self.resizing_node = node
                else: self.dragging_node = node
                self.drag_start_x, self.drag_start_y = event.x, event.y; self.refresh_editor(); return
        self.dragging_node = self.resizing_node = self.connecting_node = self.selected_node = None
        self.refresh_editor()

    def on_drag(self, event):
        dx, dy = event.x - self.drag_start_x, event.y - self.drag_start_y
        if self.dragging_node: self.move_recursive(self.dragging_node, dx, dy)
        elif self.resizing_node: 
            self.resizing_node.ui_w = max(100, self.resizing_node.ui_w + dx)
            self.resizing_node.ui_h = max(50, self.resizing_node.ui_h + dy)
        elif self.connecting_node:
            self.canvas.coords(self.temp_line, self.connecting_node.ui_x+self.connecting_node.ui_w, 
                               self.connecting_node.ui_y+self.connecting_node.ui_h/2, event.x, event.y)
        self.drag_start_x, self.drag_start_y = event.x, event.y; self.refresh_editor()

    def move_recursive(self, a, dx, dy):
        a.ui_x += dx; a.ui_y += dy
        if isinstance(a, LoopAction):
            for c in a.children: self.move_recursive(c, dx, dy)

    def on_release(self, event):
        if self.connecting_node:
            t = self.find_node_at(event.x, event.y, exclude=self.connecting_node)
            self.connecting_node.next_id = t.uid if t else None
            self.canvas.delete("temp")
        elif self.dragging_node:
            l = self.find_loop_at(event.x, event.y, exclude=self.dragging_node)
            if l: self.reparent(self.dragging_node, l)
            else: self.check_unparent(self.dragging_node)
        self.dragging_node = self.resizing_node = self.connecting_node = None; self.refresh_editor()

    def find_node_at(self, x, y, exclude=None):
        for a in reversed(self.get_flat_sequence(self.actions)):
            if a != exclude:
                if a.ui_x < x < a.ui_x+a.ui_w and a.ui_y < y < a.ui_y+a.ui_h: return a
        return None

    def find_loop_at(self, x, y, exclude=None):
        for a in reversed(self.get_flat_sequence(self.actions)):
            if isinstance(a, LoopAction) and a != exclude:
                if a.ui_x < x < a.ui_x + a.ui_w and a.ui_y < y < a.ui_y + a.ui_h: return a
        return None

    def reparent(self, a, p): self.remove_from_tree(a, self.actions); p.children.append(a)
    def check_unparent(self, a):
        if a in self.actions: return
        p = self.find_parent(a, self.actions)
        if p and not (p.ui_x < a.ui_x < p.ui_x+p.ui_w and p.ui_y < a.ui_y < p.ui_y+p.ui_h):
            self.remove_from_tree(a, self.actions); self.actions.append(a)

    def find_parent(self, t, s):
        for a in s:
            if isinstance(a, LoopAction):
                if t in a.children: return a
                r = self.find_parent(t, a.children); 
                if r: return r
        return None

    def remove_from_tree(self, t, s):
        if t in s: s.remove(t); return True
        for a in s:
            if isinstance(a, LoopAction) and self.remove_from_tree(t, a.children): return True
        return False

    def find_by_uid(self, uid, s):
        for a in s:
            if str(a.uid) == str(uid): return a
            if isinstance(a, LoopAction):
                r = self.find_by_uid(uid, a.children); 
                if r: return r
        return None

    def on_double_click(self, event):
        t = self.find_node_at(event.x, event.y)
        if t: self.show_edit_dialog(t, event)

    def show_edit_dialog(self, a, event):
        d = tk.Toplevel(self.root); d.title("編輯設定"); d.resizable(False, False)
        d.geometry(f"+{event.x_root+10}+{event.y_root+10}")
        f = ttk.Frame(d, padding=15); f.pack()
        vs = {}
        items = [("X 座標", "x"), ("Y 座標", "y"), ("點擊後等待 (秒)", "delay")] if isinstance(a, ClickAction) else [("等待秒數", "seconds")] if isinstance(a, SleepAction) else [("重複次數", "count")]
        for i, (l, k) in enumerate(items):
            ttk.Label(f, text=l).grid(row=i, column=0, sticky="w", pady=2); v = tk.StringVar(value=str(getattr(a, k)))
            ttk.Entry(f, textvariable=v, width=15).grid(row=i, column=1, pady=2); vs[k] = v
        row = len(items)
        if isinstance(a, ClickAction):
            ttk.Label(f, text="按鍵類型").grid(row=row, column=0, sticky="w"); b_v = tk.StringVar(value="左鍵" if a.button=="left" else "右鍵")
            ttk.Combobox(f, textvariable=b_v, values=["左鍵", "右鍵"], width=13).grid(row=row, column=1); vs["button"] = b_v; row+=1
        ttk.Label(f, text="備註註解").grid(row=row, column=0, sticky="w", pady=2)
        c_v = tk.StringVar(value=a.comment)
        ttk.Entry(f, textvariable=c_v, width=15).grid(row=row, column=1, pady=2); vs["comment"] = c_v
        def save():
            try:
                for k, v in vs.items():
                    val = v.get()
                    if k == "button": a.button = "left" if val=="左鍵" else "right"
                    else: setattr(a, k, int(val) if k in ["x", "y", "count"] else float(val) if k in ["delay", "seconds"] else val)
                self.refresh_editor(); d.destroy()
            except: messagebox.showerror("錯誤", "數值格式不正確")
        ttk.Button(f, text="儲存", command=save).grid(row=row+1, column=0, columnspan=2, pady=10)

    def on_right_click(self, event):
        t = self.find_node_at(event.x, event.y)
        m = tk.Menu(self.root, tearoff=0)
        if t:
            m.add_command(label="複製", command=lambda: self.duplicate_action(t))
            m.add_command(label="刪除", command=lambda: self.delete_action(t))
        else:
            m.add_command(label="新增點擊", command=lambda: self.add_click_at(event.x, event.y))
            m.add_command(label="新增等待", command=lambda: self.add_sleep_at(event.x, event.y))
            m.add_command(label="新增迴圈", command=lambda: self.add_loop_dialog(event.x, event.y))
        m.post(event.x_root, event.y_root)

    def on_delete_key(self, event):
        if self.selected_node: self.delete_action(self.selected_node)
    def add_click_at(self, x, y): self.actions.append(ClickAction(0, 0, "left", "single", ui_x=x, ui_y=y)); self.refresh_editor()
    def add_sleep_at(self, x, y): self.actions.append(SleepAction(1.0, ui_x=x, ui_y=y)); self.refresh_editor()
    def add_loop_dialog(self, x, y): self.actions.append(LoopAction(count=2, ui_x=x, ui_y=y)); self.refresh_editor()
    def duplicate_action(self, a):
        n = copy.deepcopy(a); n.uid = str(uuid.uuid4()); n.ui_x += 30; n.ui_y += 30
        p = self.find_parent(a, self.actions); (p.children if p else self.actions).append(n)
        self.refresh_editor()
    def delete_action(self, a): self.remove_from_tree(a, self.actions); self.refresh_editor()
    def clear_actions(self): 
        if messagebox.askyesno("清除", "確定要清空嗎？"): self.actions = []; self.refresh_editor()
    def play_sequence(self):
        if not self.actions: return
        self.player = Player(self.actions, self.update_status); self.root.iconify()
        threading.Thread(target=lambda: [self.player.play(), self.root.after(0, self.done_playing)], daemon=True).start()
    def done_playing(self): self.root.deiconify(); self.status_var.set("執行完畢")
    def update_status(self, m): self.root.after(0, lambda: self.status_var.set(m))
    def import_file(self):
        p = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if p:
            with open(p, 'r') as f: self.actions = deserialize_actions(f.read())
            self.refresh_editor()
    def export_file(self):
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if p:
            with open(p, 'w') as f: f.write(serialize_actions(self.actions))
    def show_about(self):
        messagebox.showinfo("關於", "Click 小幫手 v1.0\n\n熱鍵:\n- F10: 錄製/停止錄製 (雙向切換)\n- F11: 播放中斷\n- Delete: 刪除物件\n\n作者: AlexW")

    def set_sleep_prevention(self, status: bool):
        """控制系統是否可以進入睡眠模式 (支援 Windows / macOS)"""
        if sys.platform == 'win32':
            try:
                import ctypes
                ES_CONTINUOUS = 0x80000000
                ES_SYSTEM_REQUIRED = 0x00000001
                ES_DISPLAY_REQUIRED = 0x00000002
                if status:
                    ctypes.windll.kernel32.SetThreadExecutionState(
                        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
                else:
                    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            except Exception as e:
                print(f"無法設定睡眠防護: {e}")
        elif sys.platform == 'darwin':
            try:
                if status:
                    self._caffeinate_proc = subprocess.Popen(['caffeinate', '-di'])
                else:
                    if self._caffeinate_proc:
                        self._caffeinate_proc.terminate()
                        self._caffeinate_proc = None
            except Exception as e:
                print(f"無法設定睡眠防護: {e}")

    def on_close(self):
        """關閉程式時的處理"""
        self.set_sleep_prevention(False)
        self.root.destroy()

if __name__ == "__main__":
    t = tk.Tk(); app = ClickMasterApp(t); t.mainloop()
