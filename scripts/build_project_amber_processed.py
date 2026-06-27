from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from genshin_lore_db.io import ensure_dir, pretty_json_dumps, read_json, safe_filename, write_json


SOURCE = "project_amber"

LANGUAGE_LABELS = {
    "ko": "한국어",
    "zh-Hans": "중국어_간체",
    "ja": "일본어",
    "en": "영어",
    "und": "공통",
}

CONTENT_PATHS = {
    "avatar": ["캐릭터"],
    "weapon": ["무기"],
    "reliquary": ["성유물"],
    "gcg": ["일곱 성인의 소환"],
    "quest": ["여행 기록"],
    "achievement": ["업적"],
    "food": ["아카이브", "음식"],
    "material": ["아카이브", "재료"],
    "furniture": ["아카이브", "가구"],
    "furnitureSuite": ["아카이브", "가구 세트"],
    "namecard": ["아카이브", "명함"],
    "monster": ["아카이브", "생물지"],
    "book": ["아카이브", "서적"],
    "elements": ["가이드북", "원소"],
    "pronoun": ["보조 데이터", "대명사"],
    "everything": ["보조 데이터", "전체 검색 인덱스"],
    "manualWeapon": ["보조 데이터", "스탯 표기명"],
    "combine": ["보조 데이터", "제작"],
    "dailyDungeon": ["보조 데이터", "요일 비경"],
    "upgrade": ["보조 데이터", "육성 재료표"],
    "tower": ["보조 데이터", "나선 비경"],
    "static_changelog": ["보조 데이터", "변경 내역"],
    "avatarCurve": ["보조 데이터", "성장 곡선", "캐릭터"],
    "weaponCurve": ["보조 데이터", "성장 곡선", "무기"],
    "reliquaryCurve": ["보조 데이터", "성장 곡선", "성유물"],
    "monsterCurve": ["보조 데이터", "성장 곡선", "마물"],
    "event": ["보조 데이터", "이벤트"],
    "advanced_avatar_guide": ["보조 데이터", "고급 가이드", "캐릭터"],
    "advanced_weapon_guide": ["보조 데이터", "고급 가이드", "무기"],
    "advanced_reliquary_guide": ["보조 데이터", "고급 가이드", "성유물"],
}

QUEST_TYPE_LABELS = {
    "aq": "마신 임무",
    "lq": "전설 임무",
    "eq": "이벤트 임무",
    "wq": "월드 임무",
    "iq": "일일 의뢰",
    "": "기타",
    None: "기타",
}

DAY_LABELS = {
    "monday": "월요일",
    "tuesday": "화요일",
    "wednesday": "수요일",
    "thursday": "목요일",
    "friday": "금요일",
    "saturday": "토요일",
    "sunday": "일요일",
}

ADVANCED_GUIDE_SOURCE_TYPES = {
    "advanced_avatar_guide": "avatar",
    "advanced_weapon_guide": "weapon",
    "advanced_reliquary_guide": "reliquary",
}

SINGLE_LIST_FILES = {
    "pronoun": "대명사 치환표",
    "everything": "전체 검색 인덱스",
    "manualWeapon": "스탯 표기명",
    "avatarCurve": "캐릭터 성장 곡선",
    "weaponCurve": "무기 성장 곡선",
    "reliquaryCurve": "성유물 성장 곡선",
    "monsterCurve": "마물 성장 곡선",
}


class ProcessedBuilder:
    def __init__(self, root: Path, *, clean: bool = True) -> None:
        self.root = root
        self.raw_root = root / "data" / "raw" / SOURCE
        self.out_root = root / "data" / "processed" / SOURCE
        self.clean = clean
        self.used_paths: set[Path] = set()
        self.title_index: dict[tuple[str, str, str], str] = {}
        self.counts: Counter[str] = Counter()
        self.file_counts: Counter[str] = Counter()

    def run(self) -> dict[str, Any]:
        if not self.raw_root.exists():
            raise FileNotFoundError(f"Missing raw root: {self.raw_root}")
        if self.clean:
            self._clean_output()
        ensure_dir(self.out_root)

        self._build_title_index()
        self._write_all_lists()
        self._write_all_details()
        self._write_all_deep()

        report = {
            "source": SOURCE,
            "raw_root": str(self.raw_root),
            "output_root": str(self.out_root),
            "files_written": sum(self.file_counts.values()),
            "by_content_type": dict(sorted(self.counts.items())),
            "by_language": dict(sorted(self.file_counts.items())),
            "note": "data/raw/project_amber 원본은 수정하지 않고, 읽기 쉬운 사본만 생성했습니다.",
        }
        write_json(self.out_root / "_생성_보고서.json", report)
        return report

    def _clean_output(self) -> None:
        processed_root = (self.root / "data" / "processed").resolve()
        output = self.out_root.resolve()
        if output.exists():
            if processed_root not in output.parents and output != processed_root:
                raise RuntimeError(f"Refusing to remove unexpected path: {output}")
            shutil.rmtree(output)

    def _build_title_index(self) -> None:
        for list_path in sorted(self.raw_root.glob("*/*/list.raw.json")):
            record = read_json(list_path)
            language = record["language"]
            content_type = record["metadata"]["content_type"]
            payload = record.get("payload")
            if not isinstance(payload, dict):
                continue
            items = payload.get("items")
            if isinstance(items, dict):
                for item_id, item in items.items():
                    title = self._title_for_item(content_type, item, language, str(item_id))
                    self.title_index[(language, content_type, str(item_id))] = title
            if content_type == "achievement":
                for group_id, group in payload.items():
                    if not isinstance(group, dict):
                        continue
                    group_title = self._title_for_item(content_type, group, language, str(group_id))
                    self.title_index[(language, "achievement_group", str(group_id))] = group_title

        for detail_path in sorted(self.raw_root.glob("*/*/detail/*.raw.json")):
            record = read_json(detail_path)
            language = record["language"]
            content_type = record["metadata"]["content_type"]
            item_id = str(record["metadata"].get("item_id") or detail_path.stem.removesuffix(".raw"))
            title = self._title_for_record(record, fallback=item_id)
            self.title_index[(language, content_type, item_id)] = title

    def _write_all_lists(self) -> None:
        for list_path in sorted(self.raw_root.glob("*/*/list.raw.json")):
            record = read_json(list_path)
            content_type = record["metadata"]["content_type"]
            if content_type == "achievement":
                self._write_achievement_list(record, list_path)
            elif content_type == "elements":
                self._write_elements_list(record, list_path)
            elif content_type == "combine":
                self._write_mapping_items(record, list_path, folder_suffix=None)
            elif content_type == "dailyDungeon":
                self._write_daily_dungeon(record, list_path)
            elif content_type == "upgrade":
                self._write_upgrade(record, list_path)
            elif content_type == "tower":
                self._write_mapping_items(record, list_path, folder_suffix=None)
            elif content_type == "static_changelog":
                self._write_mapping_items(record, list_path, folder_suffix=None)
            elif content_type == "event":
                self._write_event_list(record, list_path)
            elif content_type in SINGLE_LIST_FILES:
                self._write_single_list(record, list_path, SINGLE_LIST_FILES[content_type])
            elif content_type in CONTENT_PATHS:
                self._write_single_list(record, list_path, "목록")

    def _write_all_details(self) -> None:
        for detail_path in sorted(self.raw_root.glob("*/*/detail/*.raw.json")):
            record = read_json(detail_path)
            content_type = record["metadata"]["content_type"]
            if content_type in {"event", *ADVANCED_GUIDE_SOURCE_TYPES.keys()}:
                self._write_special_detail(record, detail_path)
                continue
            self._write_regular_detail(record, detail_path)

    def _write_all_deep(self) -> None:
        for deep_path in sorted(self.raw_root.glob("*/*/deep/**/*.raw.json")):
            record = read_json(deep_path)
            content_type = record["metadata"]["content_type"]
            language = record["language"]
            item_id = str(record["metadata"].get("item_id") or "unknown")
            parent_title = (
                record["metadata"].get("parent_title")
                or record["metadata"].get("title")
                or self.title_index.get((language, content_type, item_id))
                or item_id
            )
            parent_folder = safe_human_filename(parent_title, max_length=64)
            base_dir = self._base_dir(language, content_type) / "_보충 데이터" / parent_folder
            title = record["metadata"].get("title") or record["metadata"].get("section") or record["metadata"].get("deep_kind")
            deep_kind = record["metadata"].get("deep_kind") or "deep"
            filename = f"{deep_kind} - {title or record['metadata'].get('deep_id') or item_id}"
            self._write_processed_json(
                base_dir,
                filename,
                record,
                deep_path,
                title=str(title or parent_title),
                extra={"parent_title": parent_title},
                max_filename_length=72,
            )

    def _write_regular_detail(self, record: dict[str, Any], raw_path: Path) -> None:
        language = record["language"]
        content_type = record["metadata"]["content_type"]
        item_id = str(record["metadata"].get("item_id") or raw_path.stem.removesuffix(".raw"))
        base_dir = self._base_dir(language, content_type)
        if content_type == "quest":
            info = record.get("payload", {}).get("info") if isinstance(record.get("payload"), dict) else {}
            quest_type = info.get("type") if isinstance(info, dict) else None
            base_dir = base_dir / QUEST_TYPE_LABELS.get(quest_type, "기타")
        title = self._title_for_record(record, fallback=item_id)
        self._write_processed_json(base_dir, title, record, raw_path, title=title)

    def _write_special_detail(self, record: dict[str, Any], raw_path: Path) -> None:
        language = record["language"]
        content_type = record["metadata"]["content_type"]
        item_id = str(record["metadata"].get("item_id") or raw_path.stem.removesuffix(".raw"))
        base_dir = self._base_dir(language, content_type)
        if content_type in ADVANCED_GUIDE_SOURCE_TYPES:
            source_type = ADVANCED_GUIDE_SOURCE_TYPES[content_type]
            parent_title = self.title_index.get(("en", source_type, item_id), item_id)
            title = f"{parent_title} 고급 가이드"
        else:
            title = self._title_for_record(record, fallback=item_id)
        self._write_processed_json(base_dir, title, record, raw_path, title=title)

    def _write_achievement_list(self, record: dict[str, Any], raw_path: Path) -> None:
        language = record["language"]
        base_dir = self._base_dir(language, "achievement")
        payload = record.get("payload")
        if not isinstance(payload, dict):
            self._write_single_list(record, raw_path, "업적 목록")
            return
        self._write_single_list(record, raw_path, "업적 전체 목록")
        for group_id, group in sorted(payload.items(), key=lambda pair: str(pair[0])):
            if not isinstance(group, dict):
                continue
            group_title = self._title_for_item("achievement", group, language, str(group_id))
            group_dir = base_dir / safe_human_filename(group_title)
            achievement_list = group.get("achievementList", {})
            achievement_items = achievement_list.items() if isinstance(achievement_list, dict) else enumerate(achievement_list or [])
            for achievement_key, achievement in achievement_items:
                if not isinstance(achievement, dict):
                    continue
                details = achievement.get("details")
                detail_items = details if isinstance(details, list) and details else [achievement]
                for detail in detail_items:
                    if not isinstance(detail, dict):
                        continue
                    achievement_id = str(detail.get("id") or achievement.get("id") or achievement_key)
                    title = self._title_for_item("achievement", detail, language, achievement_id)
                    mini_record = self._derived_record(
                        record,
                        payload={
                            "group": {k: v for k, v in group.items() if k != "achievementList"},
                            "achievement": achievement,
                            "detail": detail,
                        },
                        item_id=achievement_id,
                        kind="achievement",
                    )
                    self._write_processed_json(group_dir, title, mini_record, raw_path, title=title)

    def _write_elements_list(self, record: dict[str, Any], raw_path: Path) -> None:
        language = record["language"]
        base_dir = self._base_dir(language, "elements")
        payload = record.get("payload")
        if not isinstance(payload, dict):
            self._write_single_list(record, raw_path, "원소")
            return
        self._write_single_list(record, raw_path, "원소 전체 목록")
        info = payload.get("info")
        if isinstance(info, dict):
            title = self._title_for_item("elements", info.get("resonance", info), language, "기본 정보")
            self._write_derived_payload(record, raw_path, base_dir / "기본 정보", title, info, "info")
        for section, folder in [("resonance", "원소 공명"), ("tutorials", "원소 반응"), ("tips", "로딩 화면 팁")]:
            section_payload = payload.get(section, {})
            if not isinstance(section_payload, dict):
                continue
            for item_id, item in sorted(section_payload.items(), key=lambda pair: str(pair[0])):
                title = self._title_for_item("elements", item, language, f"{folder} {item_id}")
                self._write_derived_payload(record, raw_path, base_dir / folder, title, item, str(item_id))

    def _write_daily_dungeon(self, record: dict[str, Any], raw_path: Path) -> None:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            self._write_single_list(record, raw_path, "요일 비경")
            return
        base_dir = self._base_dir(record["language"], "dailyDungeon")
        for day, item in sorted(payload.items(), key=lambda pair: str(pair[0])):
            self._write_derived_payload(record, raw_path, base_dir, DAY_LABELS.get(day, str(day)), item, str(day))

    def _write_upgrade(self, record: dict[str, Any], raw_path: Path) -> None:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            self._write_single_list(record, raw_path, "육성 재료표")
            return
        base_dir = self._base_dir(record["language"], "upgrade")
        labels = {"avatar": "캐릭터", "weapon": "무기"}
        for section, item in sorted(payload.items(), key=lambda pair: str(pair[0])):
            self._write_derived_payload(record, raw_path, base_dir, labels.get(section, str(section)), item, str(section))

    def _write_mapping_items(self, record: dict[str, Any], raw_path: Path, *, folder_suffix: str | None) -> None:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            self._write_single_list(record, raw_path, folder_suffix or "목록")
            return
        base_dir = self._base_dir(record["language"], record["metadata"]["content_type"])
        if folder_suffix:
            base_dir = base_dir / folder_suffix
        for item_id, item in sorted(payload.items(), key=lambda pair: str(pair[0])):
            title = self._title_for_item(record["metadata"]["content_type"], item, record["language"], str(item_id))
            self._write_derived_payload(record, raw_path, base_dir, title, item, str(item_id))

    def _write_event_list(self, record: dict[str, Any], raw_path: Path) -> None:
        self._write_single_list(record, raw_path, "이벤트 목록")

    def _write_single_list(self, record: dict[str, Any], raw_path: Path, title: str) -> None:
        base_dir = self._base_dir(record["language"], record["metadata"]["content_type"])
        self._write_processed_json(base_dir, title, record, raw_path, title=title)

    def _write_derived_payload(
        self,
        source_record: dict[str, Any],
        raw_path: Path,
        base_dir: Path,
        title: str,
        payload: Any,
        item_id: str,
    ) -> None:
        record = self._derived_record(source_record, payload=payload, item_id=item_id, kind="list_item")
        self._write_processed_json(base_dir, title, record, raw_path, title=title)

    def _derived_record(self, source_record: dict[str, Any], *, payload: Any, item_id: str, kind: str) -> dict[str, Any]:
        metadata = dict(source_record.get("metadata", {}))
        metadata.update({"item_id": item_id, "kind": kind})
        return {
            "source": source_record["source"],
            "source_url": source_record["source_url"],
            "language": source_record["language"],
            "metadata": metadata,
            "payload": payload,
        }

    def _write_processed_json(
        self,
        directory: Path,
        title_for_filename: str,
        record: dict[str, Any],
        raw_path: Path,
        *,
        title: str,
        extra: dict[str, Any] | None = None,
        max_filename_length: int = 120,
    ) -> None:
        content_type = record.get("metadata", {}).get("content_type", "unknown")
        language = record.get("language", "unknown")
        output = {
            "title": title,
            "language": language,
            "content_type": content_type,
            "source": record.get("source"),
            "source_url": record.get("source_url"),
            "raw_ref": str(raw_path),
            "metadata": record.get("metadata", {}),
            "payload": record.get("payload"),
        }
        if extra:
            output.update(extra)
        path = self._unique_path(directory, title_for_filename, max_length=max_filename_length)
        ensure_dir(path.parent)
        path.write_text(pretty_json_dumps(output) + "\n", encoding="utf-8")
        self.counts[content_type] += 1
        self.file_counts[LANGUAGE_LABELS.get(language, language)] += 1

    def _unique_path(self, directory: Path, title: str, *, max_length: int = 120) -> Path:
        filename = safe_human_filename(title, max_length=max_length)
        candidate = directory / f"{filename}.json"
        if candidate not in self.used_paths and not candidate.exists():
            self.used_paths.add(candidate)
            return candidate
        index = 2
        while True:
            candidate = directory / f"{filename} ({index}).json"
            if candidate not in self.used_paths and not candidate.exists():
                self.used_paths.add(candidate)
                return candidate
            index += 1

    def _base_dir(self, language: str, content_type: str) -> Path:
        language_dir = LANGUAGE_LABELS.get(language, language)
        path_parts = CONTENT_PATHS.get(content_type, ["기타", content_type])
        return self.out_root.joinpath(language_dir, *path_parts)

    def _title_for_record(self, record: dict[str, Any], *, fallback: str) -> str:
        content_type = record.get("metadata", {}).get("content_type")
        language = record.get("language", "und")
        payload = record.get("payload")
        if content_type == "quest" and isinstance(payload, dict):
            info = payload.get("info")
            if isinstance(info, dict):
                return quest_title(info, fallback)
        if isinstance(payload, dict):
            return self._title_for_item(str(content_type), payload, language, fallback)
        item_id = str(record.get("metadata", {}).get("item_id") or fallback)
        indexed = self.title_index.get((language, str(content_type), item_id))
        return indexed or fallback

    def _title_for_item(self, content_type: str, item: Any, language: str, fallback: str) -> str:
        if not isinstance(item, dict):
            return str(fallback)
        if content_type == "quest":
            return quest_title(item, fallback)
        if content_type == "combine":
            result = item.get("resultItem")
            result_title = multilingual_title(result, language) if isinstance(result, dict) else None
            return result_title or title_from_fields(item, language) or str(fallback)
        if content_type == "static_changelog":
            version = item.get("version")
            return f"버전 {version}" if version else str(fallback)
        title = title_from_fields(item, language)
        if title:
            return title
        route = item.get("route")
        if isinstance(route, str) and route.strip():
            return route
        return str(fallback)


def quest_title(info: dict[str, Any], fallback: str) -> str:
    chapter_num = info.get("chapterNum")
    chapter_title = info.get("chapterTitle")
    route = info.get("route")
    parts = [part for part in [chapter_num, chapter_title] if isinstance(part, str) and part.strip()]
    if parts:
        return " - ".join(parts)
    if isinstance(route, str) and route.strip():
        return route
    return str(fallback)


def title_from_fields(item: dict[str, Any], language: str) -> str | None:
    for field in ["name", "title", "chapterTitle", "nameFull"]:
        value = item.get(field)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, dict):
            text = multilingual_title(value, language)
            if text:
                return text
    info = item.get("info")
    if isinstance(info, dict):
        return title_from_fields(info, language)
    return None


def multilingual_title(value: dict[str, Any], language: str) -> str | None:
    language_order = {
        "ko": ["KR", "ko", "EN", "en", "JP", "CHS"],
        "zh-Hans": ["CHS", "zh-Hans", "EN", "KR", "JP"],
        "ja": ["JP", "ja", "EN", "KR", "CHS"],
        "en": ["EN", "en", "KR", "JP", "CHS"],
        "und": ["KR", "EN", "JP", "CHS"],
    }.get(language, ["KR", "EN", "JP", "CHS"])
    for key in language_order:
        text = value.get(key)
        if isinstance(text, str) and text.strip():
            return text
    for text in value.values():
        if isinstance(text, str) and text.strip():
            return text
    return None


def safe_human_filename(value: Any, *, max_length: int = 120) -> str:
    text = str(value).strip()
    text = "".join(" " if ord(char) < 32 else char for char in text)
    for char in '<>:"/\\|?*':
        text = text.replace(char, " ")
    text = " ".join(text.split())
    if len(text) > max_length:
        text = text[:max_length].rstrip()
    text = text.rstrip(" .")
    return text or safe_filename("unknown")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--no-clean", action="store_true")
    args = parser.parse_args()
    builder = ProcessedBuilder(Path(args.root).resolve(), clean=not args.no_clean)
    report = builder.run()
    print(report)


if __name__ == "__main__":
    main()
