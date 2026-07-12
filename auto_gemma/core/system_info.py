"""OS / RAM / VRAM / GPU 감지 (Qt 비의존, 순수 파이썬).

VRAM 감지 우선순위:
  1) nvidia-smi (정확, NVIDIA 전용)
  2) Windows 레지스트리 HardwareInformation.qwMemorySize (64-bit, 벤더 무관)
  3) 실패 시 0 (통합 그래픽 추정)

주의: Win32_VideoController.AdapterRAM 은 32-bit 부호 값으로 4GB 에서 캡되어
      최신 GPU 에서 신뢰할 수 없으므로 VRAM 용도로 사용하지 않는다(이름만 사용).
"""
from __future__ import annotations

import json
import platform
import subprocess
from dataclasses import dataclass, field

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

# Windows 에서 콘솔 창 플래시 방지
_CREATE_NO_WINDOW = 0x08000000 if platform.system() == "Windows" else 0


def _run(cmd: list[str], timeout: float = 8.0) -> str | None:
    try:
        out = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=_CREATE_NO_WINDOW,
        )
        if out.returncode == 0:
            return out.stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return None


@dataclass
class SystemInfo:
    os_name: str = "Unknown"
    arch: str = ""
    ram_gb: float = 0.0
    vram_gb: float = 0.0
    gpus: list[str] = field(default_factory=list)
    vram_source: str = "none"  # nvidia-smi | registry | macos | unified | none

    @property
    def os_line(self) -> str:
        pretty = {"Windows": "Windows", "Darwin": "macOS", "Linux": "Linux"}.get(
            self.os_name, self.os_name
        )
        return f"{pretty} ({self.arch})" if self.arch else pretty

    @property
    def unified_memory(self) -> bool:
        return self.vram_source == "unified"

    @property
    def gpu_line(self) -> str:
        return ", ".join(self.gpus) if self.gpus else "감지되지 않음"


# ---------------------------------------------------------------------------
# RAM / OS
# ---------------------------------------------------------------------------
def _ram_gb() -> float:
    if psutil is not None:
        return round(psutil.virtual_memory().total / (1024 ** 3), 1)
    return 0.0


# ---------------------------------------------------------------------------
# GPU 이름 (PowerShell CIM)
# ---------------------------------------------------------------------------
def _gpu_names() -> list[str]:
    system = platform.system()
    if system == "Darwin":
        return _gpu_names_macos()
    if system == "Windows":
        out = _run([
            "powershell", "-NoProfile", "-Command",
            "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
        ])
        if out:
            return [ln.strip() for ln in out.splitlines() if ln.strip()]
        return []
    # 리눅스 폴백
    out = _run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
    if out:
        return [ln.strip() for ln in out.splitlines() if ln.strip()]
    return []


def _gpu_names_macos() -> list[str]:
    out = _run(["system_profiler", "SPDisplaysDataType"])
    names = []
    if out:
        for ln in out.splitlines():
            ln = ln.strip()
            if ln.startswith("Chipset Model:"):
                names.append(ln.split(":", 1)[1].strip())
    if not names:
        # Apple Silicon 칩 이름으로 폴백
        brand = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
        if brand and brand.strip():
            names.append(f"{brand.strip()} GPU")
    return names


# ---------------------------------------------------------------------------
# VRAM
# ---------------------------------------------------------------------------
def _vram_nvidia_gb() -> float:
    out = _run([
        "nvidia-smi", "--query-gpu=memory.total",
        "--format=csv,noheader,nounits",
    ])
    if not out:
        return 0.0
    best = 0.0
    for ln in out.splitlines():
        ln = ln.strip()
        if ln.isdigit():
            best = max(best, int(ln) / 1024.0)  # MiB → GiB
    return round(best, 1)


def _vram_registry_gb() -> float:
    if platform.system() != "Windows":
        return 0.0
    try:
        import winreg
    except ImportError:
        return 0.0
    base = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
    best = 0
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as k:
            for i in range(16):
                try:
                    with winreg.OpenKey(k, f"{i:04d}") as sk:
                        val, _ = winreg.QueryValueEx(sk, "HardwareInformation.qwMemorySize")
                        best = max(best, int(val))
                except OSError:
                    continue
    except OSError:
        return 0.0
    return round(best / (1024 ** 3), 1) if best else 0.0


def _is_apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def _vram_macos_gb(ram_gb: float) -> tuple[float, str]:
    """Apple Silicon 은 통합 메모리(RAM 공유). Intel Mac 은 discrete VRAM 파싱."""
    if _is_apple_silicon():
        # GPU 가 시스템 메모리를 공유. 대략 사용 가능한 몫(~70%)을 VRAM 으로 취급.
        return round(ram_gb * 0.7, 1), "unified"
    # Intel Mac: system_profiler 에서 "VRAM (Total): N GB" 파싱
    out = _run(["system_profiler", "SPDisplaysDataType"])
    if out:
        for ln in out.splitlines():
            ln = ln.strip()
            if ln.startswith("VRAM"):
                for tok in ln.replace(":", " ").split():
                    if tok.isdigit():
                        val = int(tok)
                        # MB 단위면 GB 로 환산
                        return (round(val / 1024, 1) if val > 512 else float(val)), "macos"
    return 0.0, "none"


def _detect_vram(ram_gb: float = 0.0) -> tuple[float, str]:
    if platform.system() == "Darwin":
        return _vram_macos_gb(ram_gb)
    v = _vram_nvidia_gb()
    if v > 0:
        return v, "nvidia-smi"
    v = _vram_registry_gb()
    if v > 0:
        return v, "registry"
    return 0.0, "none"


# ---------------------------------------------------------------------------
# 통합 감지
# ---------------------------------------------------------------------------
def detect() -> SystemInfo:
    ram = _ram_gb()
    vram, source = _detect_vram(ram)
    return SystemInfo(
        os_name=platform.system() or "Unknown",
        arch=platform.machine(),
        ram_gb=ram,
        vram_gb=vram,
        gpus=_gpu_names(),
        vram_source=source,
    )


if __name__ == "__main__":  # 수동 확인용
    info = detect()
    print(json.dumps(info.__dict__, ensure_ascii=False, indent=2))
