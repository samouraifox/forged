"""LangGraph adaptive RAG state machine (Phase B Day 8-9).

Routes queries by difficulty. EASY queries get the fast linear path
(hybrid+rerank -> CRAG grade -> generate). HARD queries get multi-query
rewriting, HyDE, multi-strategy union retrieval, CRAG grade, and one
optional retry when CRAG average relevance is below threshold.

Reuses RetrieveService for the retrieval stack (Chroma + BM25 + reranker).
All auxiliary LLM calls go to the already-loaded Hermes-4-14B via the
OpenAI-compatible llama-server endpoint; no new model loads.
"""

from __future__ import annotations

import re
import time
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from openai import OpenAI
from pydantic import BaseModel, ConfigDict

from rag.service import (
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    NO_RETRIEVED_CONTEXT,
    NO_THINK_INSTRUCTION,
    RAG_PROMPT_TEMPLATE,
    RAG_RUNTIME_SYSTEM,
    QueryConfig,
    RetrieveService,
    ThinkTagStreamParser,
    format_context,
    hybrid_search,
    rerank,
)

CLIENT = OpenAI(base_url=LLM_BASE_URL, api_key="not-needed")

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

CRAG_THRESHOLD = 0.5
MAX_RETRIES = 1
DEFAULT_TOPK = 5

# Module-level service ref so node functions (which only see GraphState) can
# reach the live retrieval stack. Set by build_adaptive_app() / adaptive_query.
_SERVICE: RetrieveService | None = None


def _strip_think(text: str) -> str:
    return _THINK_BLOCK_RE.sub("", text).strip()


def _llm_call(
    user_prompt: str,
    *,
    max_tokens: int,
    temperature: float = LLM_TEMPERATURE,
    think: bool = False,
    system_extra: str = "",
) -> str:
    """Non-streaming auxiliary call. Returns assistant content with <think>
    blocks removed. Used by classify / multi-query / HyDE / grade nodes."""
    system_parts = ["Answer concisely."]
    if system_extra:
        system_parts.append(system_extra)
    if not think:
        system_parts.append(NO_THINK_INSTRUCTION)
    system = "\n".join(system_parts)
    response = CLIENT.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
        stream=False,
    )
    return _strip_think(response.choices[0].message.content or "")


def _parse_binary(response: str, positive: str, negative: str, default: str) -> str:
    text = response.upper()
    p = text.find(positive)
    n = text.find(negative)
    if p == -1 and n == -1:
        return default
    if p == -1:
        return negative
    if n == -1:
        return positive
    return positive if p < n else negative


class GraphState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    query: str
    branch: Literal["easy", "hard"] | None = None
    rewritten_queries: list[str] = []
    hyde_doc: str | None = None
    retrieved_chunks: list[dict] = []
    relevance_grades: dict[str, float] = {}
    avg_relevance: float | None = None
    retry_count: int = 0
    final_context: list[dict] = []
    answer: str | None = None

    # Telemetry (additive beyond the brief spec; needed for diagnostics)
    classify_decision: str | None = None
    timing: dict[str, float] = {}
    status_log: list[str] = []
    thinking_text: str = ""


# --- Node functions ---------------------------------------------------------


def classify_query(state: GraphState) -> dict[str, Any]:
    t0 = time.perf_counter()
    prompt = (
        "Classify this query as EASY or HARD.\n"
        "EASY = specific entity (CVE ID, tool name, single technique), single topic.\n"
        "HARD = multi-topic, comparative, exploratory, ambiguous, no clear entity.\n"
        f"Query: {state.query}\n"
        "Reply with ONE WORD: EASY or HARD."
    )
    response = _llm_call(prompt, max_tokens=4, temperature=0.0)
    decision = _parse_binary(response, "EASY", "HARD", default="EASY")
    branch = "easy" if decision == "EASY" else "hard"
    elapsed = time.perf_counter() - t0
    timing = dict(state.timing)
    timing["classify_s"] = elapsed
    return {
        "branch": branch,
        "classify_decision": decision,
        "timing": timing,
        "status_log": state.status_log
        + [f"[classify] raw={response[:40]!r} -> {decision} ({branch}) ({elapsed*1000:.0f}ms)"],
    }


def retrieve_simple(state: GraphState) -> dict[str, Any]:
    t0 = time.perf_counter()
    assert _SERVICE is not None, "adaptive_pipeline._SERVICE must be initialized"
    config = QueryConfig(think=True, rag=True, topk=DEFAULT_TOPK)
    hits = _SERVICE.retrieve_top_hits(state.query, config, history=[])
    elapsed = time.perf_counter() - t0
    timing = dict(state.timing)
    timing["retrieve_simple_s"] = elapsed
    return {
        "retrieved_chunks": hits,
        "timing": timing,
        "status_log": state.status_log + [f"[retrieve_simple] {len(hits)} hits ({elapsed*1000:.0f}ms)"],
    }


def multi_query_rewrite(state: GraphState) -> dict[str, Any]:
    t0 = time.perf_counter()
    hint = ""
    if state.retry_count > 0:
        hint = (
            "Previous retrieval attempt did not surface relevant content. "
            "Try noticeably different semantic angles this time.\n"
        )
    prompt = (
        "Generate 2 alternative phrasings of this query for document retrieval.\n"
        "Focus on different semantic angles while retaining all key entities "
        "(CVE IDs, tool names, ATT&CK technique IDs).\n"
        f"Query: {state.query}\n"
        f"{hint}"
        "Output one phrasing per line. No numbering, no preamble."
    )
    response = _llm_call(prompt, max_tokens=200, temperature=0.4)
    variants = [line.strip().lstrip("-*0123456789. ").strip() for line in response.splitlines()]
    variants = [
        v for v in variants
        if len(v) > 8 and not v.lower().startswith(("here", "sure", "okay", "alternative"))
    ]
    variants = variants[:3]
    elapsed = time.perf_counter() - t0
    timing = dict(state.timing)
    timing["multi_query_s"] = elapsed
    return {
        "rewritten_queries": variants,
        "timing": timing,
        "status_log": state.status_log
        + [f"[multi_query] {len(variants)} variants ({elapsed*1000:.0f}ms)"],
    }


def retrieve_with_hyde(state: GraphState) -> dict[str, Any]:
    t0 = time.perf_counter()
    hyde_prompt = (
        "Write a brief hypothetical answer to the following query.\n"
        "Focus on technical content with specific entities, terms, and details. "
        "Aim for ~100 words.\n"
        f"Query: {state.query}"
    )
    hyde_doc = _llm_call(hyde_prompt, max_tokens=300, temperature=0.4)

    assert _SERVICE is not None
    hits = hybrid_search(hyde_doc, _SERVICE.col, _SERVICE.bm25, _SERVICE.bm25_data)
    by_id: dict[str, dict] = {h["id"]: h for h in state.retrieved_chunks}
    new_count = 0
    for h in hits:
        if h["id"] not in by_id:
            by_id[h["id"]] = h
            new_count += 1
    elapsed = time.perf_counter() - t0
    timing = dict(state.timing)
    timing["hyde_s"] = elapsed
    return {
        "hyde_doc": hyde_doc,
        "retrieved_chunks": list(by_id.values()),
        "timing": timing,
        "status_log": state.status_log
        + [f"[hyde] doc={len(hyde_doc)} chars, +{new_count} new hits ({elapsed*1000:.0f}ms)"],
    }


def retrieve_multi_query(state: GraphState) -> dict[str, Any]:
    t0 = time.perf_counter()
    assert _SERVICE is not None
    by_id: dict[str, dict] = {h["id"]: h for h in state.retrieved_chunks}
    queries_to_run = [state.query, *state.rewritten_queries]
    for q in queries_to_run:
        if not q.strip():
            continue
        hits = hybrid_search(q, _SERVICE.col, _SERVICE.bm25, _SERVICE.bm25_data)
        for h in hits:
            by_id.setdefault(h["id"], h)
    pool = list(by_id.values())
    if pool:
        reranked = rerank(state.query, pool, DEFAULT_TOPK, _SERVICE.reranker)
    else:
        reranked = []
    elapsed = time.perf_counter() - t0
    timing = dict(state.timing)
    timing["multi_retrieve_s"] = elapsed
    return {
        "retrieved_chunks": reranked,
        "timing": timing,
        "status_log": state.status_log
        + [f"[multi_retrieve] pool={len(pool)} -> top-{len(reranked)} ({elapsed*1000:.0f}ms)"],
    }


def grade_relevance(state: GraphState) -> dict[str, Any]:
    t0 = time.perf_counter()
    grades: dict[str, float] = {}
    yes_count = 0
    for hit in state.retrieved_chunks:
        chunk_text = hit.get("doc") or ""
        prompt = (
            f"Query: {state.query}\n"
            f"Document: {chunk_text[:500]}\n"
            "Is this document relevant to answering the query? Reply YES or NO."
        )
        response = _llm_call(prompt, max_tokens=4, temperature=0.0)
        decision = _parse_binary(response, "YES", "NO", default="NO")
        grades[hit["id"]] = 1.0 if decision == "YES" else 0.0
        if decision == "YES":
            yes_count += 1
    avg = (yes_count / len(state.retrieved_chunks)) if state.retrieved_chunks else 0.0
    elapsed = time.perf_counter() - t0
    timing = dict(state.timing)
    timing.setdefault("grade_s", 0.0)
    timing["grade_s"] += elapsed
    return {
        "relevance_grades": grades,
        "avg_relevance": avg,
        "timing": timing,
        "status_log": state.status_log
        + [f"[grade] {yes_count}/{len(state.retrieved_chunks)} YES, avg={avg:.2f} ({elapsed*1000:.0f}ms)"],
    }


def increment_retry(state: GraphState) -> dict[str, Any]:
    return {
        "retry_count": state.retry_count + 1,
        "status_log": state.status_log + [f"[retry] retry_count -> {state.retry_count + 1}"],
    }


def generate_answer(state: GraphState) -> dict[str, Any]:
    t0 = time.perf_counter()
    context_text = (
        format_context(state.retrieved_chunks) if state.retrieved_chunks else NO_RETRIEVED_CONTEXT
    )
    user_prompt = RAG_PROMPT_TEMPLATE.format(
        history="(no prior conversation)",
        context=context_text,
        question=state.query,
    )
    stream = CLIENT.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": RAG_RUNTIME_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        temperature=LLM_TEMPERATURE,
        max_tokens=4096,
        stream=True,
    )
    parser = ThinkTagStreamParser()
    answer_parts: list[str] = []
    thinking_parts: list[str] = []
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        text = getattr(delta, "content", None) or ""
        if not text:
            continue
        for in_think, segment in parser.push(text):
            (thinking_parts if in_think else answer_parts).append(segment)
    for in_think, segment in parser.finish():
        (thinking_parts if in_think else answer_parts).append(segment)
    answer = "".join(answer_parts)
    thinking = "".join(thinking_parts)
    elapsed = time.perf_counter() - t0
    timing = dict(state.timing)
    timing["generate_s"] = elapsed
    return {
        "answer": answer,
        "thinking_text": thinking,
        "final_context": state.retrieved_chunks,
        "timing": timing,
        "status_log": state.status_log
        + [
            f"[generate] answer={len(answer)} chars, thinking={len(thinking)} chars "
            f"({elapsed*1000:.0f}ms)"
        ],
    }


# --- Routing ---------------------------------------------------------------


def _route_after_classify(state: GraphState) -> str:
    return "retrieve_simple" if state.branch == "easy" else "multi_query_rewrite"


def _route_after_grade(state: GraphState) -> str:
    if state.avg_relevance is None or state.avg_relevance >= CRAG_THRESHOLD:
        return "generate_answer"
    if state.retry_count >= MAX_RETRIES:
        return "generate_answer"
    return "increment_retry"


# --- Graph builder ---------------------------------------------------------


def build_adaptive_graph():
    g = StateGraph(GraphState)
    g.add_node("classify_query", classify_query)
    g.add_node("retrieve_simple", retrieve_simple)
    g.add_node("multi_query_rewrite", multi_query_rewrite)
    g.add_node("retrieve_with_hyde", retrieve_with_hyde)
    g.add_node("retrieve_multi_query", retrieve_multi_query)
    g.add_node("grade_relevance", grade_relevance)
    g.add_node("increment_retry", increment_retry)
    g.add_node("generate_answer", generate_answer)

    g.add_edge(START, "classify_query")
    g.add_conditional_edges(
        "classify_query",
        _route_after_classify,
        {"retrieve_simple": "retrieve_simple", "multi_query_rewrite": "multi_query_rewrite"},
    )
    g.add_edge("retrieve_simple", "grade_relevance")
    g.add_edge("multi_query_rewrite", "retrieve_with_hyde")
    g.add_edge("retrieve_with_hyde", "retrieve_multi_query")
    g.add_edge("retrieve_multi_query", "grade_relevance")
    g.add_conditional_edges(
        "grade_relevance",
        _route_after_grade,
        {"generate_answer": "generate_answer", "increment_retry": "increment_retry"},
    )
    g.add_edge("increment_retry", "multi_query_rewrite")
    g.add_edge("generate_answer", END)
    return g.compile()


def attach_service(service: RetrieveService) -> None:
    """Wire a live, initialized RetrieveService for node functions to use."""
    global _SERVICE
    _SERVICE = service
