from __future__ import annotations


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 2)


def compact_dict(data: dict, max_items: int = 8) -> dict:
    compacted = {}
    for key, value in data.items():
        if isinstance(value, list):
            compacted[key] = value[:max_items]
        else:
            compacted[key] = value
    return compacted


def cost_note(summary_text: str) -> str:
    tokens = estimate_tokens(summary_text)
    return f"Token 节约：本次仅发送约 {tokens} tokens 的聚合摘要，不发送原始明细表。"
