"""Shared retrieval + generation service for the active hacker_lm backend."""

from __future__ import annotations

import pickle
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path

import chromadb
import ollama
from openai import OpenAI
from sentence_transformers import CrossEncoder

EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "hermes-4-14b"
LLM_DISPLAY_NAME = "Hermes-4-14B (Q6_K, llama-server)"
LLM_BASE_URL = "http://127.0.0.1:8080/v1"
LLM_TEMPERATURE = 0.4
LLM_MAX_TOKENS = 4096
RERANKER = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_DB = str(Path(__file__).resolve().parent / "chroma_db")
COLLECTION = "security"
VALID_SOURCES = {"hacktricks", "payloads", "owasp", "mitre"}
MAX_HISTORY_MESSAGES = 8
MAX_HISTORY_CHARS_PER_MESSAGE = 500

_LLM_CLIENT = OpenAI(base_url=LLM_BASE_URL, api_key="not-needed")

RAG_RUNTIME_SYSTEM = """Answer in ENGLISH ONLY.
Use the retrieved context as the primary source for factual claims.
Only use inline citation tags that already appear in the context block, and end supported factual claims with those tags in the form [source::rel_path].
If a claim is not supported by the context, either omit it or mark it [general-knowledge].
If the context does not cover the question, say "Context does not cover this." and then continue with a best-effort answer using [general-knowledge] for unsupported claims.
Do not fabricate CVEs, versions, flags, tool behavior, payloads, output, or exploitability.
Keep the answer direct and actionable."""

DIRECT_RUNTIME_SYSTEM = """Answer in ENGLISH ONLY.
Give a short assessment first, then the practical path forward with exact commands, payloads, code, or verification steps when relevant.
Do not fabricate CVEs, versions, flags, tool behavior, payloads, output, or exploitability.
If something is uncertain, say so briefly and continue with the best grounded next step."""

RAG_PROMPT_TEMPLATE = """Conversation so far:
{history}

Retrieved context:
{context}

User question:
{question}
"""

DIRECT_PROMPT_TEMPLATE = """Conversation so far:
{history}

User question:
{question}
"""

NO_RETRIEVED_CONTEXT = "(no retrieved context)"
NO_CONVERSATION_HISTORY = "(no prior conversation)"
NO_THINK_INSTRUCTION = "Do not use <think> blocks for this response. Answer directly."

TOKEN_RE = re.compile(r"\w+")


class QueryEventType(str, Enum):
    STATUS = "status"
    RETRIEVED_CONTEXT = "retrieved_context"
    THINKING = "thinking"
    ANSWER_CHUNK = "answer_chunk"
    ERROR = "error"
    DONE = "done"


@dataclass(frozen=True, slots=True)
class QueryEvent:
    type: QueryEventType
    text: str = ""


@dataclass(slots=True)
class QueryConfig:
    think: bool = True
    rag: bool = True
    topk: int = 5
    source: str | None = None
    show_context: bool = False

    @classmethod
    def from_mapping(cls, data: dict[str, object]) -> "QueryConfig":
        topk = int(data.get("topk", 5))
        if topk < 1 or topk > 20:
            raise ValueError("TOPK must be between 1 and 20.")
        source = data.get("source")
        source_value = str(source) if source else None
        if source_value and source_value not in VALID_SOURCES:
            raise ValueError(f"source must be one of {sorted(VALID_SOURCES)}")
        return cls(
            think=bool(data.get("think", True)),
            rag=bool(data.get("rag", True)),
            topk=topk,
            source=source_value,
            show_context=bool(data.get("show_context", data.get("ctx", False))),
        )


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def load_bm25(db_path: str):
    import bm25s

    bm25 = bm25s.BM25.load(str(Path(db_path) / "bm25s_index"))
    with open(Path(db_path) / "bm25_meta.pkl", "rb") as handle:
        meta = pickle.load(handle)
    return bm25, meta


@lru_cache(maxsize=256)
def embed(text: str):
    return ollama.embeddings(model=EMBED_MODEL, prompt=text)["embedding"]


def hybrid_search(query: str, col, bm25, bm25_data, k_dense: int = 10, k_sparse: int = 10, source_filter: str | None = None):
    where = {"source": source_filter} if source_filter else None
    q_tokens = tokenize(query)

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_embed = executor.submit(embed, query)
        future_bm25 = executor.submit(bm25.retrieve, [q_tokens], k=k_sparse, show_progress=False)
        q_vec = future_embed.result()
        sparse_idx, sparse_scores = future_bm25.result()

    dense = col.query(query_embeddings=[q_vec], n_results=k_dense, where=where)

    dense_hits = {
        dense["ids"][0][index]: {
            "id": dense["ids"][0][index],
            "doc": dense["documents"][0][index],
            "meta": dense["metadatas"][0][index],
            "dense_rank": index + 1,
        }
        for index in range(len(dense["ids"][0]))
    }

    for rank, index in enumerate(sparse_idx[0].tolist()):
        chunk_id = bm25_data["ids"][index]
        meta = bm25_data["metas"][index]
        if source_filter and meta.get("source") != source_filter:
            continue
        if chunk_id in dense_hits:
            dense_hits[chunk_id]["sparse_rank"] = rank + 1
        else:
            dense_hits[chunk_id] = {
                "id": chunk_id,
                "doc": bm25_data["docs"][index],
                "meta": meta,
                "sparse_rank": rank + 1,
            }

    k_rrf = 60
    for hit in dense_hits.values():
        score = 0.0
        if "dense_rank" in hit:
            score += 1 / (k_rrf + hit["dense_rank"])
        if "sparse_rank" in hit:
            score += 1 / (k_rrf + hit["sparse_rank"])
        hit["rrf"] = score
    return sorted(dense_hits.values(), key=lambda hit: -hit["rrf"])


def rerank(query: str, hits, top_k: int, reranker):
    pairs = [(query, hit["doc"]) for hit in hits]
    scores = reranker.predict(pairs)
    for hit, score in zip(hits, scores):
        hit["rerank"] = float(score)
    return sorted(hits, key=lambda hit: -hit["rerank"])[:top_k]


def format_context(hits) -> str:
    blocks: list[str] = []
    for hit in hits:
        tag = f'[{hit["meta"]["source"]}::{hit["meta"]["rel_path"]}]'
        blocks.append(f"{tag}\n{hit['doc']}")
    return "\n\n---\n\n".join(blocks)


def normalize_history(history: list[dict[str, object]] | None, question: str) -> list[dict[str, str]]:
    if not history:
        return []

    normalized: list[dict[str, str]] = []
    for item in history:
        role = str(item.get("role", "")).strip().lower()
        if role not in {"user", "assistant"}:
            continue
        content = _normalize_message_text(item.get("content", ""))
        if not content:
            continue
        normalized.append({"role": role, "content": content})

    latest_question = _normalize_message_text(question)
    if normalized and normalized[-1]["role"] == "user" and normalized[-1]["content"] == latest_question:
        normalized.pop()

    if len(normalized) > MAX_HISTORY_MESSAGES:
        normalized = normalized[-MAX_HISTORY_MESSAGES:]
    return normalized


def format_history(history: list[dict[str, str]]) -> str:
    if not history:
        return NO_CONVERSATION_HISTORY

    lines = []
    for item in history:
        role = "USER" if item["role"] == "user" else "ASSISTANT"
        lines.append(f"{role}: {_clip_text(item['content'])}")
    return "\n".join(lines)


def build_retrieval_query(question: str, history: list[dict[str, str]]) -> str:
    latest_question = _normalize_message_text(question)
    if not history:
        return latest_question

    recent = history[-4:]
    history_lines = [f"{item['role'].upper()}: {_clip_text(item['content'], limit=220)}" for item in recent]
    return (
        f"LATEST USER QUESTION: {latest_question}\n"
        "RECENT CONVERSATION FOR DISAMBIGUATION:\n"
        + "\n".join(history_lines)
    )


def _clip_text(text: str, *, limit: int = MAX_HISTORY_CHARS_PER_MESSAGE) -> str:
    collapsed = _normalize_message_text(text)
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 3].rstrip()}..."


def _normalize_message_text(value: object) -> str:
    return " ".join(str(value).split())


class ThinkTagStreamParser:
    _START_TAG = "<think>"
    _END_TAG = "</think>"

    def __init__(self) -> None:
        self.in_think = False
        self.tag_buffer = ""

    def push(self, chunk: str) -> list[tuple[bool, str]]:
        output: list[tuple[bool, str]] = []
        segment: list[str] = []
        for character in chunk:
            if self.tag_buffer:
                candidate = self.tag_buffer + character
                if self._is_tag_prefix(candidate):
                    self.tag_buffer = candidate
                    if candidate == self._START_TAG:
                        self.tag_buffer = ""
                        self.in_think = True
                    elif candidate == self._END_TAG:
                        self.tag_buffer = ""
                        self.in_think = False
                    continue
                segment.append(candidate)
                self.tag_buffer = ""
                continue
            if character == "<":
                self._flush(segment, output)
                self.tag_buffer = character
                continue
            segment.append(character)
        self._flush(segment, output)
        return output

    def finish(self) -> list[tuple[bool, str]]:
        output: list[tuple[bool, str]] = []
        if self.tag_buffer:
            output.append((self.in_think, self.tag_buffer))
            self.tag_buffer = ""
        self.in_think = False
        return output

    def _flush(self, segment: list[str], output: list[tuple[bool, str]]) -> None:
        if segment:
            output.append((self.in_think, "".join(segment)))
            segment.clear()

    def _is_tag_prefix(self, candidate: str) -> bool:
        return self._START_TAG.startswith(candidate) or self._END_TAG.startswith(candidate)


class RetrieveService:
    provider = "local"
    backend_name = "hacker_lm"
    model_name = LLM_DISPLAY_NAME
    think_control = "prompt-policy"

    def __init__(self, db_path: str = DEFAULT_DB) -> None:
        self.db_path = str(Path(db_path))
        self.col = None
        self.bm25 = None
        self.bm25_data = None
        self.reranker = None

    @property
    def is_ready(self) -> bool:
        return all((self.col, self.bm25, self.bm25_data, self.reranker))

    def initialize(self):
        if self.is_ready:
            return

        yield QueryEvent(QueryEventType.STATUS, f"[init] opening vector store at {self.db_path}")
        client = chromadb.PersistentClient(path=self.db_path)
        self.col = client.get_collection(COLLECTION)

        yield QueryEvent(QueryEventType.STATUS, "[init] loading BM25 index")
        self.bm25, self.bm25_data = load_bm25(self.db_path)

        yield QueryEvent(QueryEventType.STATUS, f"[init] loading reranker {RERANKER}")
        self.reranker = CrossEncoder(RERANKER)

        yield QueryEvent(QueryEventType.STATUS, f"[init] generation backend: {LLM_DISPLAY_NAME} @ {LLM_BASE_URL}")
        yield QueryEvent(QueryEventType.STATUS, f"[init] backend ready over {self.col.count()} chunks")

    def retrieve_top_hits(
        self,
        question: str,
        config: QueryConfig,
        history: list[dict[str, object]] | None = None,
    ) -> list[dict]:
        """Strictly-additive helper for offline evaluation: returns the reranked
        top-k hits as plain dicts (id, doc, meta, dense_rank, sparse_rank, rrf,
        rerank). Does not stream, does not call the LLM, does not mutate any
        instance state beyond lazy-init of the retrieval stack. Existing
        stream_query behavior is unchanged."""
        for _ in self.initialize():
            pass
        if not config.rag:
            return []
        normalized_history = normalize_history(history, question)
        retrieval_query = build_retrieval_query(question, normalized_history)
        hits = hybrid_search(
            retrieval_query,
            self.col,
            self.bm25,
            self.bm25_data,
            source_filter=config.source,
        )
        if not hits:
            return []
        return rerank(retrieval_query, hits, config.topk, self.reranker)

    def stream_query(self, question: str, config: QueryConfig, history: list[dict[str, object]] | None = None):
        if not question.strip():
            yield QueryEvent(QueryEventType.ERROR, "Prompt is empty.")
            yield QueryEvent(QueryEventType.DONE)
            return

        yield from self.initialize()
        normalized_history = normalize_history(history, question)
        history_block = format_history(normalized_history)
        retrieval_query = build_retrieval_query(question, normalized_history)

        mode = f"think={'on' if config.think else 'off'}"
        if not config.rag:
            if config.show_context:
                yield QueryEvent(
                    QueryEventType.STATUS,
                    "[ctx] CTX only shows retrieved chunks, so it has no effect while RAG is off",
                )
            yield QueryEvent(QueryEventType.STATUS, "[retrieve] disabled; sending question directly to LLM")
            yield QueryEvent(QueryEventType.STATUS, f"[llm] streaming response ({mode})…")
            t0 = time.perf_counter()
            yield from self._generate(
                prompt=DIRECT_PROMPT_TEMPLATE.format(history=history_block, question=question),
                system=DIRECT_RUNTIME_SYSTEM,
                think=config.think,
            )
            yield QueryEvent(QueryEventType.STATUS, f"[timing] llm={time.perf_counter() - t0:.2f} s")
            yield QueryEvent(QueryEventType.DONE)
            return

        source_clause = f" (source={config.source})" if config.source else ""
        yield QueryEvent(
            QueryEventType.STATUS,
            f"[retrieve] hybrid search over {self.col.count()} chunks{source_clause}…",
        )
        t0 = time.perf_counter()
        hits = hybrid_search(retrieval_query, self.col, self.bm25, self.bm25_data, source_filter=config.source)
        t_search = time.perf_counter() - t0
        top_hits = []
        t_rerank = 0.0
        if hits:
            yield QueryEvent(
                QueryEventType.STATUS,
                f"[retrieve] {len(hits)} candidates in {t_search * 1000:.0f} ms -> reranking",
            )
            t0 = time.perf_counter()
            top_hits = rerank(retrieval_query, hits, config.topk, self.reranker)
            t_rerank = time.perf_counter() - t0

            if config.show_context:
                context_lines = [
                    (
                        f"[{hit['rerank']:.3f}] {hit['meta']['source']}::{hit['meta']['rel_path']} - "
                        f"{hit['meta']['section_path']}"
                    )
                    for hit in top_hits
                ]
                yield QueryEvent(
                    QueryEventType.RETRIEVED_CONTEXT,
                    "\n".join(context_lines) if context_lines else NO_RETRIEVED_CONTEXT,
                )
        else:
            yield QueryEvent(
                QueryEventType.STATUS,
                f"[retrieve] no hits in {t_search * 1000:.0f} ms; falling back to general knowledge",
            )
            if config.show_context:
                yield QueryEvent(QueryEventType.RETRIEVED_CONTEXT, NO_RETRIEVED_CONTEXT)

        context_text = format_context(top_hits) if top_hits else NO_RETRIEVED_CONTEXT
        yield QueryEvent(
            QueryEventType.STATUS,
            (
                f"[timing] search={t_search * 1000:.0f} ms  rerank={t_rerank * 1000:.0f} ms  "
                f"retrieval_total={(t_search + t_rerank) * 1000:.0f} ms"
            ),
        )
        yield QueryEvent(QueryEventType.STATUS, f"[llm] streaming response ({mode})…")
        t0 = time.perf_counter()
        yield from self._generate(
            prompt=RAG_PROMPT_TEMPLATE.format(history=history_block, context=context_text, question=question),
            system=RAG_RUNTIME_SYSTEM,
            think=config.think,
        )
        yield QueryEvent(QueryEventType.STATUS, f"[timing] llm={time.perf_counter() - t0:.2f} s")
        yield QueryEvent(QueryEventType.DONE)

    def _generate(self, prompt: str, *, system: str, think: bool):
        effective_system = self._effective_system(system, think)
        yield from self._stream_generate(
            prompt=prompt,
            system=effective_system,
            emit_thinking=think,
        )

    def _stream_generate(self, prompt: str, *, system: str, emit_thinking: bool):
        parser = ThinkTagStreamParser()
        stream = _LLM_CLIENT.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            stream=True,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            text = getattr(delta, "content", None) or ""
            if not text:
                continue
            for in_think, segment in parser.push(text):
                if not segment:
                    continue
                if in_think and not emit_thinking:
                    continue
                yield QueryEvent(
                    QueryEventType.THINKING if in_think else QueryEventType.ANSWER_CHUNK,
                    segment,
                )
        for in_think, segment in parser.finish():
            if not segment:
                continue
            if in_think and not emit_thinking:
                continue
            yield QueryEvent(
                QueryEventType.THINKING if in_think else QueryEventType.ANSWER_CHUNK,
                segment,
            )

    def _effective_system(self, system: str, think: bool) -> str:
        if think:
            return system
        return f"{system}\n\n{NO_THINK_INSTRUCTION}"
