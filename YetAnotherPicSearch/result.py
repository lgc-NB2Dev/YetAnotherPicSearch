from typing import Any, Dict, List, Optional


class Result:
    def __init__(self, mapping: Dict[str, Any]):
        self.ascii2d: Optional[List[str]] = []
        self.saucenao: Optional[List[str]] = []
        self.whatanime: Optional[List[str]] = []
        self.ex: Optional[List[str]] = []
        self.image_md5: Optional[str] = None
        self.update_at: Optional[str] = None
        self.mode: str = "all"
        for key, value in mapping.items():
            setattr(self, key, value)
