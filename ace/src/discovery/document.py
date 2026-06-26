from dataclasses import dataclass, field
from typing import List, Optional, Dict
from ace.src.contracts.architecture_ids import ArchitectureID

@dataclass(frozen=True)
class DocumentNode:
    """Base class for all elements in the Document AST."""
    pass

@dataclass(frozen=True)
class Heading(DocumentNode):
    level: int
    text: str

@dataclass(frozen=True)
class Paragraph(DocumentNode):
    text: str

@dataclass(frozen=True)
class ListItem(DocumentNode):
    text: str

@dataclass(frozen=True)
class ListBlock(DocumentNode):
    items: List[ListItem]

@dataclass(frozen=True)
class Section(DocumentNode):
    """A Heading and all its subsequent nodes until the next heading of equal or higher level."""
    heading: Heading
    children: List[DocumentNode]
    aid: Optional[ArchitectureID] = None

@dataclass(frozen=True)
class Document(DocumentNode):
    """
    The structured Document AST representation.
    Abstracts away Markdown/AsciiDoc syntax.
    """
    file_path: str
    nodes: List[DocumentNode]
    index: Dict[str, Section] = field(default_factory=dict)

    def section(self, aid: ArchitectureID) -> Optional[Section]:
        """O(1) lookup of a section by its ArchitectureID."""
        return self.index.get(aid.id)
        
    def exists(self, aid: ArchitectureID) -> bool:
        """Returns True if the document contains the specified ArchitectureID."""
        return aid.id in self.index
