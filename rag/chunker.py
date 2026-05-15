"""Markdown-aware chunker. Splits on headings, keeps section path, enforces token budget."""
import re
from pathlib import Path
from dataclasses import dataclass, asdict

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
TARGET_TOKENS = 600
MAX_TOKENS = 900
MIN_TOKENS = 80

def approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)

@dataclass
class Chunk:
    text: str
    source: str
    rel_path: str
    section_path: str
    chunk_id: str

def split_by_headings(md: str):
    """Yield (level, title, body) for each section, preserving order."""
    positions = [(m.start(), len(m.group(1)), m.group(2).strip()) for m in HEADING_RE.finditer(md)]
    if not positions:
        yield 0, "", md
        return
    if positions[0][0] > 0:
        yield 0, "", md[: positions[0][0]]
    for i, (start, level, title) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(md)
        heading_line_end = md.find("\n", start)
        body = md[heading_line_end + 1 : end] if heading_line_end != -1 else ""
        yield level, title, body

def pack_paragraphs(body: str):
    """Greedy-pack paragraphs into chunks near TARGET_TOKENS, hard cap MAX_TOKENS."""
    paragraphs = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
    buf, buf_tokens = [], 0
    for p in paragraphs:
        t = approx_tokens(p)
        if t > MAX_TOKENS:
            if buf:
                yield "\n\n".join(buf)
                buf, buf_tokens = [], 0
            lines = p.splitlines()
            cur, cur_t = [], 0
            for line in lines:
                lt = approx_tokens(line)
                if cur_t + lt > MAX_TOKENS and cur:
                    yield "\n".join(cur)
                    cur, cur_t = [], 0
                cur.append(line)
                cur_t += lt
            if cur:
                yield "\n".join(cur)
            continue
        if buf_tokens + t > MAX_TOKENS and buf:
            yield "\n\n".join(buf)
            buf, buf_tokens = [], 0
        buf.append(p)
        buf_tokens += t
        if buf_tokens >= TARGET_TOKENS:
            yield "\n\n".join(buf)
            buf, buf_tokens = [], 0
    if buf:
        yield "\n\n".join(buf)

def chunk_markdown(md: str, source: str, rel_path: str):
    section_stack = []
    chunks = []
    idx = 0
    for level, title, body in split_by_headings(md):
        if level > 0:
            section_stack = section_stack[: level - 1]
            section_stack.append(title)
        section_path = " > ".join(section_stack) if section_stack else Path(rel_path).stem
        for piece in pack_paragraphs(body):
            piece = piece.strip()
            if approx_tokens(piece) < MIN_TOKENS:
                continue
            chunk_id = f"{source}::{rel_path}::{idx}"
            chunks.append(Chunk(
                text=f"# {section_path}\n\n{piece}",
                source=source,
                rel_path=rel_path,
                section_path=section_path,
                chunk_id=chunk_id,
            ))
            idx += 1
    return chunks

def iter_markdown_files(root: Path):
    for p in root.rglob("*.md"):
        if any(part.startswith(".") for part in p.parts):
            continue
        yield p

if __name__ == "__main__":
    import sys, json
    root = Path(sys.argv[1])
    source = sys.argv[2]
    n = 0
    for md_path in iter_markdown_files(root):
        rel = str(md_path.relative_to(root))
        try:
            md = md_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for ch in chunk_markdown(md, source, rel):
            print(json.dumps(asdict(ch)))
            n += 1
    print(f"# {n} chunks", file=sys.stderr)
