from typing import Any, Dict, List, Optional


class Result:
    def __init__(self, mapping: Dict[str, Any]):
        self.ascii2d: List[str] = []
        self.iqdb: List[str] = []
        self.saucenao: List[str] = []
        self.ex: List[str] = []
        self.image_md5: Optional[str] = None
        self.mode: str = "all"
        for key, value in mapping.items():
            setattr(self, key, value)
