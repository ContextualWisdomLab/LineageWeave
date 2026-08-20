"""Localize versioned TEPP finding codes without changing source evidence."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FINDING_KEYS = {
    "contract_award_before_focus": "An explicit contract-award event precedes the current event. This is a temporal association, not a causal conclusion.",
    "specification_change_before_focus": "An explicit specification-change event precedes the current event. This is a temporal association, not a causal conclusion.",
    "delivery_before_focus": "An explicit delivery event precedes the current event. This is a temporal association, not a causal conclusion.",
    "operational_handoff_before_focus": "An explicit operational-handoff event precedes the current event. This is a temporal association, not a causal conclusion.",
    "voc_before_focus": "An explicit VOC event precedes the current event. This is a temporal association, not a causal conclusion.",
    "rebid_after_focus": "An explicit rebid event follows the current event. This is a temporal association, not a causal conclusion.",
    "transition_gap_candidate": "A gap exists between explicitly observed project stages. The missing transition is a review candidate, not a proven cause.",
}

TRANSLATIONS = {
    "en": {value: value for value in FINDING_KEYS.values()},
    "ko": {
        FINDING_KEYS["contract_award_before_focus"]: "명시적인 수주 이벤트가 현재 이벤트보다 앞섭니다. 이는 시간적 연관이며 인과 결론이 아닙니다.",
        FINDING_KEYS["specification_change_before_focus"]: "명시적인 사양 변경 이벤트가 현재 이벤트보다 앞섭니다. 이는 시간적 연관이며 인과 결론이 아닙니다.",
        FINDING_KEYS["delivery_before_focus"]: "명시적인 납품 이벤트가 현재 이벤트보다 앞섭니다. 이는 시간적 연관이며 인과 결론이 아닙니다.",
        FINDING_KEYS["operational_handoff_before_focus"]: "명시적인 운영 인수 이벤트가 현재 이벤트보다 앞섭니다. 이는 시간적 연관이며 인과 결론이 아닙니다.",
        FINDING_KEYS["voc_before_focus"]: "명시적인 VOC 이벤트가 현재 이벤트보다 앞섭니다. 이는 시간적 연관이며 인과 결론이 아닙니다.",
        FINDING_KEYS["rebid_after_focus"]: "명시적인 재입찰 이벤트가 현재 이벤트 뒤에 있습니다. 이는 시간적 연관이며 인과 결론이 아닙니다.",
        FINDING_KEYS["transition_gap_candidate"]: "명시적으로 관찰된 프로젝트 단계 사이에 공백이 있습니다. 누락된 전환은 검토 후보일 뿐 입증된 원인이 아닙니다.",
    },
    "zh": {
        FINDING_KEYS["contract_award_before_focus"]: "明确的中标事件早于当前事件。这只是时间关联，不是因果结论。",
        FINDING_KEYS["specification_change_before_focus"]: "明确的规格变更事件早于当前事件。这只是时间关联，不是因果结论。",
        FINDING_KEYS["delivery_before_focus"]: "明确的交付事件早于当前事件。这只是时间关联，不是因果结论。",
        FINDING_KEYS["operational_handoff_before_focus"]: "明确的运营移交事件早于当前事件。这只是时间关联，不是因果结论。",
        FINDING_KEYS["voc_before_focus"]: "明确的 VOC 事件早于当前事件。这只是时间关联，不是因果结论。",
        FINDING_KEYS["rebid_after_focus"]: "明确的重新投标事件晚于当前事件。这只是时间关联，不是因果结论。",
        FINDING_KEYS["transition_gap_candidate"]: "明确观察到的项目阶段之间存在空档。缺失的转换仅是审查候选，并非已证实的原因。",
    },
    "ja": {
        FINDING_KEYS["contract_award_before_focus"]: "明示的な受注イベントが現在のイベントより前にあります。これは時間的関連であり、因果結論ではありません。",
        FINDING_KEYS["specification_change_before_focus"]: "明示的な仕様変更イベントが現在のイベントより前にあります。これは時間的関連であり、因果結論ではありません。",
        FINDING_KEYS["delivery_before_focus"]: "明示的な納品イベントが現在のイベントより前にあります。これは時間的関連であり、因果結論ではありません。",
        FINDING_KEYS["operational_handoff_before_focus"]: "明示的な運用引継ぎイベントが現在のイベントより前にあります。これは時間的関連であり、因果結論ではありません。",
        FINDING_KEYS["voc_before_focus"]: "明示的な VOC イベントが現在のイベントより前にあります。これは時間的関連であり、因果結論ではありません。",
        FINDING_KEYS["rebid_after_focus"]: "明示的な再入札イベントが現在のイベントより後にあります。これは時間的関連であり、因果結論ではありません。",
        FINDING_KEYS["transition_gap_candidate"]: "明示的に観測されたプロジェクト段階の間に空白があります。欠落した遷移はレビュー候補であり、証明された原因ではありません。",
    },
    "vi": {
        FINDING_KEYS["contract_award_before_focus"]: "Một sự kiện trúng thầu rõ ràng xảy ra trước sự kiện hiện tại. Đây là liên hệ thời gian, không phải kết luận nhân quả.",
        FINDING_KEYS["specification_change_before_focus"]: "Một sự kiện thay đổi đặc tả rõ ràng xảy ra trước sự kiện hiện tại. Đây là liên hệ thời gian, không phải kết luận nhân quả.",
        FINDING_KEYS["delivery_before_focus"]: "Một sự kiện bàn giao rõ ràng xảy ra trước sự kiện hiện tại. Đây là liên hệ thời gian, không phải kết luận nhân quả.",
        FINDING_KEYS["operational_handoff_before_focus"]: "Một sự kiện chuyển giao vận hành rõ ràng xảy ra trước sự kiện hiện tại. Đây là liên hệ thời gian, không phải kết luận nhân quả.",
        FINDING_KEYS["voc_before_focus"]: "Một sự kiện VOC rõ ràng xảy ra trước sự kiện hiện tại. Đây là liên hệ thời gian, không phải kết luận nhân quả.",
        FINDING_KEYS["rebid_after_focus"]: "Một sự kiện đấu thầu lại rõ ràng xảy ra sau sự kiện hiện tại. Đây là liên hệ thời gian, không phải kết luận nhân quả.",
        FINDING_KEYS["transition_gap_candidate"]: "Có khoảng trống giữa các giai đoạn dự án được quan sát rõ ràng. Chuyển tiếp còn thiếu chỉ là ứng viên cần xem xét, không phải nguyên nhân đã được chứng minh.",
    },
}


def patch_component() -> None:
    path = ROOT / "frontend/src/components/ProjectHistoryTimeline.tsx"
    text = path.read_text(encoding="utf-8")
    if "const FINDING_SUMMARY_KEYS" not in text:
        anchor = "const EVENT_LABEL_KEYS: Record<string, string> = {"
        start = text.index(anchor)
        end = text.index("\n};", start) + 3
        block = "\n\nconst FINDING_SUMMARY_KEYS: Record<string, string> = {\n"
        for code, key in FINDING_KEYS.items():
            block += f'  {code}: "{key}",\n'
        block += "};\n\nfunction findingSummary(finding: TeppProjectHistory[\"findings\"][number]): string {\n"
        block += "  const key = FINDING_SUMMARY_KEYS[finding.finding_code];\n"
        block += "  return key ? t(key) : finding.summary;\n"
        block += "}\n"
        text = text[:end] + block + text[end:]
    text = text.replace("{finding.summary}", "{findingSummary(finding)}")
    path.write_text(text, encoding="utf-8")


def patch_i18n() -> None:
    path = ROOT / "frontend/src/i18n.ts"
    text = path.read_text(encoding="utf-8")
    if FINDING_KEYS["specification_change_before_focus"] in text:
        return
    for locale, translations in TRANSLATIONS.items():
        anchor = f"  {locale}: {{\n"
        if text.count(anchor) != 1:
            raise RuntimeError(f"locale anchor drifted: {locale}")
        lines = "".join(
            f"    {json_key(key)}: {json_key(value)},\n"
            for key, value in translations.items()
        )
        text = text.replace(anchor, anchor + lines, 1)
    path.write_text(text, encoding="utf-8")


def json_key(value: str) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)


def patch_changelog() -> None:
    path = ROOT / "CHANGELOG.d/2.18.0-tepp-project-history-ask.md"
    text = path.read_text(encoding="utf-8")
    line = "- Localizes TEPP finding-code explanations while retaining source-post evidence and the non-causal boundary.\n"
    if line not in text:
        path.write_text(text + line, encoding="utf-8")


def main() -> None:
    patch_component()
    patch_i18n()
    patch_changelog()


if __name__ == "__main__":
    main()
