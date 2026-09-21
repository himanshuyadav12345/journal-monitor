from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class Article:
    journal: str
    journal_id: str
    title: str
    url: str
    doi: Optional[str] = None
    published: Optional[str] = None
    updated: Optional[str] = None
    item_type: Optional[str] = None
    source: Optional[str] = None
    issue: Optional[str] = None
    stage: Optional[str] = None

    def to_dict(self):
        return asdict(self)
