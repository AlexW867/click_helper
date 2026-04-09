import time
import pyautogui
from models import ClickAction, SleepAction, LoopAction

class Player:
    def __init__(self, actions, status_callback):
        self.actions = actions
        self.status_callback = status_callback
        self.stop_requested = False

    def request_stop(self):
        self.stop_requested = True
        self.status_callback("使用者停止 (F11)")

    def play(self):
        self.stop_requested = False
        if self.actions:
            self.status_callback("準備執行 (2秒後開始)...")
            time.sleep(2)
            if self.stop_requested: return

            entry = self.find_entry_node(self.actions)
            if entry: self.execute_flow(entry, self.actions)

    def find_entry_node(self, nodes):
        if not nodes: return None
        pointed = {n.next_id for n in nodes if n.next_id}
        entries = [n for n in nodes if n.uid not in pointed]
        return entries[0] if entries else nodes[0]

    def execute_flow(self, start_node, context_nodes):
        all_nodes = self.get_all_nodes(self.actions)
        id_map = {n.uid: n for n in all_nodes}
        current = start_node
        while current and not self.stop_requested:
            label = "左鍵" if (isinstance(current, ClickAction) and current.button == 'left') else \
                    "右鍵" if (isinstance(current, ClickAction) and current.button == 'right') else \
                    "等待" if isinstance(current, SleepAction) else "迴圈"
            self.status_callback(f"執行中: {label}")
            
            if isinstance(current, ClickAction):
                # We skip current.delay if it was meant to be BEFORE? No, the user says "點擊後等待"
                pyautogui.click(x=current.x, y=current.y, button=current.button, clicks=(2 if current.type == "double" else 1))
                time.sleep(current.delay)
            elif isinstance(current, SleepAction):
                time.sleep(current.seconds)
            elif isinstance(current, LoopAction):
                for loop_idx in range(current.count):
                    if self.stop_requested: break
                    self.status_callback(f"迴圈中 ({loop_idx+1}/{current.count})")
                    if current.children:
                        loop_entry = self.find_entry_node(current.children)
                        self.execute_sub_flow(loop_entry, current.children, id_map)
            
            if current.next_id in id_map: current = id_map[current.next_id]
            else: break

    def execute_sub_flow(self, start_node, sub_nodes, id_map):
        sub_uids = {n.uid for n in sub_nodes}
        current = start_node
        while current and not self.stop_requested:
            if isinstance(current, ClickAction):
                pyautogui.click(x=current.x, y=current.y, button=current.button, clicks=(2 if current.type == "double" else 1))
                time.sleep(current.delay)
            elif isinstance(current, SleepAction):
                time.sleep(current.seconds)
            elif isinstance(current, LoopAction):
                for loop_idx in range(current.count):
                    if self.stop_requested: break
                    if current.children:
                        inner_entry = self.find_entry_node(current.children)
                        self.execute_sub_flow(inner_entry, current.children, id_map)
            
            if current.next_id in sub_uids: current = id_map[current.next_id]
            else: break

    def get_all_nodes(self, actions):
        res = []
        for a in actions:
            res.append(a)
            if hasattr(a, 'children'): res.extend(self.get_all_nodes(a.children))
        return res
