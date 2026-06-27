from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from genshin_lore_db.normalize import clean_text


ROUTE_MODES = {"basic_lookup", "summary", "analysis", "research"}

GAME_INFO_TERMS = {
    "효과",
    "옵션",
    "스탯",
    "재료",
    "돌파",
    "특성",
    "세트",
    "성유물",
    "무기",
    "캐릭터",
    "레벨",
    "어떻게 얻",
    "어디서 얻",
}

SUMMARY_TERMS = {
    "요약",
    "줄거리",
    "내용 정리",
    "정리해",
    "무슨 내용",
    "스토리 정리",
}

RESEARCH_TERMS = {
    "깊게",
    "심층",
    "가설",
    "가능성",
    "추측",
    "떡밥",
    "연결",
    "비교",
    "검증",
    "반례",
    "세계관",
    "정체",
}

RELATION_TERMS = {
    "관련",
    "관계",
    "같은",
    "동일",
    "계승",
    "상징",
    "의미",
    "근거",
}


@dataclass(frozen=True)
class RouteDecision:
    mode: str
    confidence: float
    signals: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def route_query(
    message: str,
    *,
    workspace_context: dict[str, Any] | None = None,
    user_settings: dict[str, Any] | None = None,
) -> RouteDecision:
    text = clean_text(message)
    lowered = text.casefold()
    workspace_context = workspace_context or {}
    user_settings = user_settings or {}

    if user_settings.get("default_depth") == "research":
        return RouteDecision(
            mode="research",
            confidence=0.86,
            signals=["user_default_depth:research"],
            reason="사용자 설정이 기본 연구 모드입니다.",
        )

    if workspace_context.get("current_mode") == "research" and looks_like_followup(lowered):
        return RouteDecision(
            mode="research",
            confidence=0.78,
            signals=["workspace_current_mode:research", "followup"],
            reason="현재 워크스페이스가 연구 모드이고 후속 질문으로 보입니다.",
        )

    summary_hits = keyword_hits(lowered, SUMMARY_TERMS)
    research_hits = keyword_hits(lowered, RESEARCH_TERMS)
    relation_hits = keyword_hits(lowered, RELATION_TERMS)
    game_info_hits = keyword_hits(lowered, GAME_INFO_TERMS)

    if game_info_hits and not research_hits and not relation_hits:
        return RouteDecision(
            mode="basic_lookup",
            confidence=0.82,
            signals=[f"game_info:{hit}" for hit in game_info_hits[:4]],
            reason="성유물, 무기, 재료, 효과 같은 단순 게임 정보 조회로 분류했습니다.",
        )

    if summary_hits and not research_hits:
        return RouteDecision(
            mode="summary",
            confidence=0.78,
            signals=[f"summary:{hit}" for hit in summary_hits[:4]],
            reason="문서나 스토리 요약 요청으로 분류했습니다.",
        )

    if research_hits:
        confidence = 0.72 + min(len(research_hits) * 0.04, 0.18)
        if relation_hits:
            confidence += 0.04
        return RouteDecision(
            mode="research",
            confidence=min(confidence, 0.94),
            signals=[f"research:{hit}" for hit in research_hits[:5]] + [f"relation:{hit}" for hit in relation_hits[:3]],
            reason="가설, 가능성, 연결, 반례처럼 깊은 탐색이 필요한 표현이 있습니다.",
        )

    if relation_hits:
        return RouteDecision(
            mode="analysis",
            confidence=0.74,
            signals=[f"relation:{hit}" for hit in relation_hits[:5]],
            reason="스토리 관계성 분석 요청으로 분류했습니다.",
        )

    return RouteDecision(
        mode="analysis",
        confidence=0.55,
        signals=["default:analysis"],
        reason="명확한 단순 조회나 요약 요청이 아니므로 기본 분석 모드로 분류했습니다.",
    )


def keyword_hits(text: str, keywords: set[str]) -> list[str]:
    return [keyword for keyword in sorted(keywords, key=len, reverse=True) if keyword.casefold() in text]


def looks_like_followup(text: str) -> bool:
    followup_terms = ["그럼", "그러면", "이어서", "아까", "그 관점", "반대로", "다시", "그건"]
    return any(term in text for term in followup_terms) or len(text.split()) <= 8
