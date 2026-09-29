from pydantic import BaseModel
from typing import List, Optional

class HindsightMemory(BaseModel):
    id: str
    content: str
    metadata: Optional[dict] = {}
