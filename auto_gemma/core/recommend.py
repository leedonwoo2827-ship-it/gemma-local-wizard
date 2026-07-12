"""VRAM·RAM 기준 Gemma 모델 추천 + 제한 요인 판정 (Qt 비의존)."""
from __future__ import annotations

from dataclasses import dataclass

from auto_gemma.app.config import CATALOG_BY_TAG, ModelSpec, spec_for


@dataclass
class Recommendation:
    model: ModelSpec
    limiting_factor: str      # "VRAM" | "RAM" | "없음"
    limiting_value_gb: float
    gpu_accelerated: bool

    def summary(self) -> str:
        accel = "GPU 가속" if self.gpu_accelerated else "CPU 실행"
        return f"{self.model.label} ({self.model.tag}) · {accel}"

    def limit_text(self) -> str:
        if self.limiting_factor == "없음":
            return "제한 요인: 없음 — 더 큰 모델도 무리 없이 실행 가능합니다."
        return (
            f"제한 요인: {self.limiting_factor} "
            f"({self.limiting_value_gb:g}GB) — 이것 때문에 더 큰 모델을 못 골랐어요."
        )


# VRAM 임계값 → 후보 모델 (높은 것부터). 8GB → gemma3:4b (레퍼런스 일치)
_TIERS: list[tuple[float, str]] = [
    (24.0, "gemma3:27b"),
    (12.0, "gemma3:12b"),
    (6.0, "gemma3:4b"),
    (0.0, "gemma3:1b"),
]


def recommend(vram_gb: float, ram_gb: float) -> Recommendation:
    """VRAM 우선으로 티어를 고르되, RAM 부족 시 한 단계씩 내린다."""
    # 1) VRAM 기준 후보 선택
    chosen_tag = "gemma3:1b"
    for min_vram, tag in _TIERS:
        if vram_gb >= min_vram:
            chosen_tag = tag
            break

    model = CATALOG_BY_TAG[chosen_tag]
    gpu_accel = vram_gb >= model.vram_gb

    # 2) RAM 부족 시 다운그레이드
    ram_limited = False
    order = [t for _, t in _TIERS]  # 큰→작은
    idx = order.index(chosen_tag)
    while ram_gb < CATALOG_BY_TAG[order[idx]].ram_gb and idx < len(order) - 1:
        idx += 1
        ram_limited = True
    model = CATALOG_BY_TAG[order[idx]]
    gpu_accel = vram_gb >= model.vram_gb

    # 3) 제한 요인 판정
    if ram_limited:
        factor, value = "RAM", ram_gb
    elif chosen_tag != "gemma3:27b":
        # 더 큰 모델을 못 고른 이유가 VRAM (통합/미감지면 VRAM 0)
        factor = "VRAM"
        value = vram_gb
    else:
        factor, value = "없음", vram_gb

    return Recommendation(
        model=model,
        limiting_factor=factor,
        limiting_value_gb=value,
        gpu_accelerated=gpu_accel,
    )
