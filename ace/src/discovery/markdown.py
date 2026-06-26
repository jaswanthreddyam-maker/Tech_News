import os
import re
from typing import Dict, Any, List
from ace.src.contracts.capability import CapabilityProvider
from ace.src.contracts.architecture_ids import AIDRegistry
from ace.src.discovery.document import (
    Document, DocumentNode, Heading, Paragraph, ListItem, ListBlock, Section
)

class MarkdownProvider(CapabilityProvider):
    """
    Parses Markdown files into the structured Document AST.
    Extracts explicit `<!-- aid: namespace.id -->` tags into the AST index.
    """
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self._cache: Dict[str, Document] = {}
        self._preload_cache()

    @property
    def capability_type(self) -> str:
        return "markdown"

    def discover(self) -> Dict[str, Document]:
        return self._cache

    def version(self) -> str:
        return "1.0.0"

    def _preload_cache(self):
        docs_dir = os.path.join(self.root_dir, "docs")
        if not os.path.exists(docs_dir):
            return
            
        for dirpath, _, filenames in os.walk(docs_dir):
            for file in filenames:
                if file.endswith(".md"):
                    full_path = os.path.join(dirpath, file)
                    rel_path = os.path.relpath(full_path, self.root_dir).replace("\\", "/")
                    self._cache[rel_path] = self._parse_markdown(full_path, rel_path)

    def _parse_markdown(self, full_path: str, rel_path: str) -> Document:
        nodes: List[DocumentNode] = []
        index: Dict[str, Section] = {}
        
        with open(full_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        current_section_heading = None
        current_section_children = []
        current_aid = None
        
        in_list = False
        current_list_items = []
        
        def push_section():
            if current_section_heading:
                section = Section(heading=current_section_heading, children=current_section_children.copy(), aid=current_aid)
                nodes.append(section)
                if current_aid:
                    index[current_aid.id] = section
            else:
                nodes.extend(current_section_children)
                
        def push_list():
            nonlocal in_list, current_list_items
            if in_list and current_list_items:
                current_section_children.append(ListBlock(items=current_list_items.copy()))
                current_list_items.clear()
                in_list = False
                
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
                
            heading_match = re.match(r"^(#+)\s+(.*)", line_str)
            if heading_match:
                push_list()
                push_section()
                
                level = len(heading_match.group(1))
                text = heading_match.group(2)
                current_section_heading = Heading(level=level, text=text)
                current_section_children = []
                current_aid = None
                continue
                
            # Look for aid tags: <!-- aid: constitution.principles -->
            aid_match = re.match(r"<!--\s*aid:\s*([a-zA-Z0-9_\.]+)\s*-->", line_str)
            if aid_match:
                try:
                    aid_id = aid_match.group(1)
                    # Lookup registry to guarantee valid AID assignment
                    current_aid = AIDRegistry.get(aid_id)
                except KeyError:
                    # In a robust engine we would emit a diagnostic warning for unregistered AIDs
                    pass
                continue
                
            list_match = re.match(r"^(\d+\.|\*|\-)\s+(.*)", line_str)
            if list_match:
                in_list = True
                current_list_items.append(ListItem(text=list_match.group(2)))
                continue
                
            push_list()
            current_section_children.append(Paragraph(text=line_str))
            
        push_list()
        push_section()
        
        return Document(file_path=rel_path, nodes=nodes, index=index)

    def get_data(self) -> Dict[str, Document]:
        return self._cache
