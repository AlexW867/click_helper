import json
import uuid
from dataclasses import dataclass, field
from typing import List, Union, Optional

@dataclass
class ClickAction:
    x: int
    y: int
    button: str
    type: str
    delay: float = 1.0
    description: str = ""
    comment: str = ""
    action_type: str = "click"
    ui_x: int = 50
    ui_y: int = 50
    ui_w: int = 200
    ui_h: int = 85
    next_id: Optional[str] = None
    uid: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class SleepAction:
    seconds: float
    description: str = ""
    comment: str = ""
    action_type: str = "sleep"
    ui_x: int = 50
    ui_y: int = 50
    ui_w: int = 200
    ui_h: int = 85
    next_id: Optional[str] = None
    uid: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class LoopAction:
    count: int
    children: List['Action'] = field(default_factory=list)
    description: str = ""
    comment: str = ""
    action_type: str = "loop"
    ui_x: int = 50
    ui_y: int = 50
    ui_w: int = 250
    ui_h: int = 200
    next_id: Optional[str] = None
    uid: str = field(default_factory=lambda: str(uuid.uuid4()))

Action = Union[ClickAction, SleepAction, LoopAction]

def serialize_actions(actions: List[Action]) -> str:
    def _to_dict(a):
        d = vars(a).copy()
        if hasattr(a, 'children'):
            d['children'] = [_to_dict(c) for c in a.children]
        return d
    return json.dumps([_to_dict(a) for a in actions], indent=2)

def deserialize_actions(data_str: str) -> List[Action]:
    data = json.loads(data_str)
    
    def _from_dict(d):
        a_type = d.get("action_type")
        if a_type == "click":
            # Backward compatibility check for ui_w/h
            if "ui_w" not in d: d["ui_w"] = 200
            if "ui_h" not in d: d["ui_h"] = 85
            return ClickAction(**{k: v for k, v in d.items() if k != "action_type"})
        elif a_type == "sleep":
            if "ui_w" not in d: d["ui_w"] = 200
            if "ui_h" not in d: d["ui_h"] = 85
            return SleepAction(**{k: v for k, v in d.items() if k != "action_type"})
        elif a_type == "loop":
            children_data = d.pop("children", [])
            loop = LoopAction(**{k: v for k, v in d.items() if k != "action_type"})
            loop.children = [_from_dict(c) for c in children_data]
            return loop
            
    return [_from_dict(item) for item in data]
