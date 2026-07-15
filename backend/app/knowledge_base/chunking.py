# Enable modern string-based type hinting to prevent version evaluation crashes
from __future__ import annotations

import re
from dataclasses import dataclass

# Define the standard maximum character volume threshold for our database slices
DEFAULT_MAX_CHUNK_CHARS = 1200
CHARS_PER_TOKEN = 4

# Regex flags to isolate Markdown Section Headers (#, ##, ###) safely
_HEADER_RE = re.compile(r"^(#{1,3})\s+(.*)$", re.MULTILINE)

# Advanced sentence-splitter that ignores dots inside decimals (e.g. 10.50)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\u00C0-\u024F])")


@dataclass
class MarkdownSection:
    """Structure tracking a full document heading section and its contents."""
    section_path: str   # Keeps track of heading parents (e.g., 'Shoes > Sneakers')
    heading_level: int  # The hashtag count depth (1 for #, 2 for ##)
    content: str        # The raw text body inside this heading section


@dataclass
class TextChunk:
    """The final safe paragraph snippet text block saved to PostgreSQL."""
    section_path: str
    content: str


def split_markdown_into_sections(markdown_text: str) -> list[MarkdownSection]:
    """Scans raw file text to split the content cleanly by heading structures."""
    matches = list(_HEADER_RE.finditer(markdown_text))
    sections: list[MarkdownSection] = []
    breadcrumb: dict[int, str] = {} # Dict tracking active heading history map

    # If the document has zero hashtags, treat the entire file as one section block
    if not matches:
        body = markdown_text.strip()
        if body:
            sections.append(MarkdownSection(section_path="", heading_level=0, content=body))
        return sections

    # Capture any introduction paragraphs typed before the first heading hashtag
    leading = markdown_text[: matches[0].start()].strip()
    if leading:
        sections.append(MarkdownSection(section_path="", heading_level=0, content=leading))

    # Loop through all detected section headers across the text
    for i, match in enumerate(matches):
        level = len(match.group(1))     # Count hashtags to detect depth level
        title = match.group(2).strip()  # Clean up title text strings

        # Update the active breadcrumb folder map history
        breadcrumb[level] = title
        # Wipe out any deeper sub-folder logs left over from a previous loop track
        for deeper in list(breadcrumb.keys()):
            if deeper > level:
                del breadcrumb[deeper]

        # String-join active parents together (e.g. 'Clothes > Summer > Dresses')
        path = " > ".join(breadcrumb[lvl] for lvl in sorted(breadcrumb) if lvl <= level)

        # Calculate exact character index pointers to extract the body string text
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown_text)
        body = markdown_text[start:end].strip()

        # If text is inside, wrap it into a safe section structure object
        if body:
            sections.append(MarkdownSection(section_path=path, heading_level=level, content=body))

    return sections


def chunk_section(
    section: MarkdownSection,
    max_chars: int = DEFAULT_MAX_CHUNK_CHARS,
) -> list[TextChunk]:
    """Takes a long document section and breaks it into smaller paragraph slices."""
    content = section.content
    # If the text body is already small enough, skip slicing loops entirely
    if len(content) <= max_chars:
        return [TextChunk(section_path=section.section_path, content=content)]

    # Break text block by sentence end points
    sentences = _SENTENCE_SPLIT_RE.split(content)
    chunks: list[TextChunk] = []
    current: list[str] = []
    current_len = 0

    # Group sentences together until they hit our maximum character limit
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # FIX: Handle rare run-on sentences that are naturally larger than max_chars limit
        if len(sentence) > max_chars:
            # If we already have items in the current buffer, flush them first
            if current:
                chunks.append(TextChunk(section_path=section.section_path, content=" ".join(current)))
                current = []
                current_len = 0
            
            # Sub-split the monster sentence on word spaces safely
            words = sentence.split(" ")
            sub_current: list[str] = []
            sub_len = 0
            for word in words:
                if sub_len + len(word) + 1 > max_chars and sub_current:
                    chunks.append(TextChunk(section_path=section.section_path, content=" ".join(sub_current)))
                    sub_current = []
                    sub_len = 0
                sub_current.append(word)
                sub_len += len(word) + 1
            if sub_current:
                current = sub_current
                current_len = sub_len
            continue

        # If adding the next sentence overfills our block, save the current group
        if current_len + len(sentence) + 1 > max_chars and current:
            chunks.append(TextChunk(section_path=section.section_path, content=" ".join(current)))
            current = []
            current_len = 0
            
        current.append(sentence)
        current_len += len(sentence) + 1

    # Catch any remaining text lines left inside the tracking buffer
    if current:
        chunks.append(TextChunk(section_path=section.section_path, content=" ".join(current)))

    return chunks


def chunk_markdown_document(
    markdown_text: str,
    max_chars: int = DEFAULT_MAX_CHUNK_CHARS,
) -> list[TextChunk]:
    """Core entry pipeline method to completely chunk any multi-page document file."""
    sections = split_markdown_into_sections(markdown_text)
    chunks: list[TextChunk] = []
    for section in sections:
        chunks.extend(chunk_section(section, max_chars=max_chars))
    return chunks


# --- THE KENYAN MARKETPLACE 'K' EXTRACTION ENGINE ---

# Scans inputs for digits followed by a 'k' or 'K' character word boundary tag
_NUMERIC_SHORTHAND_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*[kK]\b")


def _expand_k_shorthand(match: re.Match) -> str:
    """Takes a 'K' string match regex object and expands its numerical value."""
    value = float(match.group(1))
    expanded = value * 1000 # Expand thousand multipliers in RAM memory
    if expanded.is_integer():
        return str(int(expanded)) # Format clean whole numbers as a string (1500)
    return str(expanded)


def normalize_query_for_retrieval(query: str) -> str:
    """Main input query cleaner to translate shorthand 'k' characters into true numbers."""
    return _NUMERIC_SHORTHAND_RE.sub(_expand_k_shorthand, query)