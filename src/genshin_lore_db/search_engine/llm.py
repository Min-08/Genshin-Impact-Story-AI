from __future__ import annotations

from typing import Any

from genshin_lore_db.normalize import clean_text


def build_reasoning_prompt(investigation: dict[str, Any], *, max_items: int = 24) -> dict[str, Any]:
    query = investigation.get("query") or ""
    evidence_items = flatten_evidence(investigation, max_items=max_items)
    context_blocks = []
    for index, item in enumerate(evidence_items, start=1):
        label = f"[{index}] {item.get('title') or item.get('source_id') or item.get('id')} / {item.get('language')} / {item.get('category')}"
        context_blocks.append(
            {
                "label": label,
                "source_id": item.get("source_id") or item.get("id"),
                "canonical_id": item.get("canonical_id"),
                "source_url": item.get("source_url"),
                "raw_refs": item.get("raw_refs") or [],
                "text": clean_text(item.get("excerpt") or item.get("text") or ""),
            }
        )
    system = "\n".join(
        [
            "너는 원신 스토리 추측 프로젝트의 근거 분석 엔진이다.",
            "반드시 제공된 근거와 언어별 표현 차이를 우선 사용한다.",
            "확정 사실, 강한 추측, 약한 추측, 반박 가능성을 분리한다.",
            "고유명사는 한국어 표기를 우선 사용하되 필요한 경우 원문 표기를 병기한다.",
            "근거가 부족한 연결은 단정하지 않는다.",
        ]
    )
    user = "\n".join(
        [
            f"조사 주제: {query}",
            "",
            "아래 근거 블록을 바탕으로 한국어 보고서를 작성하라.",
            "출력 구조:",
            "1. 핵심 결론",
            "2. 확정 사실",
            "3. 강한 추측",
            "4. 약한 추측",
            "5. 반박 가능성",
            "6. 더 조사할 연결고리",
        ]
    )
    return {
        "provider_ready": True,
        "planned_providers": ["local_llama", "gemini_api"],
        "system": system,
        "user": user,
        "context_blocks": context_blocks,
        "notes": [
            "이 패키지는 API 호출을 수행하지 않습니다.",
            "로컬 Llama에는 system/user/context_blocks를 합쳐 단일 프롬프트로 넘기면 됩니다.",
            "Gemini API에는 system instruction과 user content parts로 분리해 넘기면 됩니다.",
        ],
    }


def flatten_evidence(investigation: dict[str, Any], *, max_items: int) -> list[dict[str, Any]]:
    seen = set()
    rows: list[dict[str, Any]] = []
    for item in (investigation.get("evidence_pack") or {}).get("sources") or []:
        add_evidence(rows, seen, item, max_items=max_items)
        if len(rows) >= max_items:
            return rows
    for group in investigation.get("evidence_groups") or []:
        for item in group.get("items") or []:
            if "items" in item and "canonical_id" in item:
                for nested in item.get("items") or []:
                    add_evidence(rows, seen, nested, max_items=max_items)
            else:
                add_evidence(rows, seen, item, max_items=max_items)
            if len(rows) >= max_items:
                return rows
    for item in investigation.get("results") or []:
        add_evidence(rows, seen, item, max_items=max_items)
        if len(rows) >= max_items:
            break
    return rows


def add_evidence(rows: list[dict[str, Any]], seen: set[str], item: dict[str, Any], *, max_items: int) -> None:
    item_id = str(item.get("source_id") or item.get("id") or item.get("chunk_id") or item.get("textmap_id") or "")
    if not item_id or item_id in seen or len(rows) >= max_items:
        return
    seen.add(item_id)
    rows.append(item)
