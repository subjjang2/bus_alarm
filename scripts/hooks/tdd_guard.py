#!/usr/bin/env python3
"""TDD Guard hook — PreToolUse[Edit|Write].

src/ 아래 구현 코드(.py)를 쓰기 전에 대응하는 tests/test_<module>.py가
이미 존재하는지 확인한다. 없으면 차단한다 (테스트를 먼저 작성하라는 취지).

Claude Code(Edit/Write, tool_input.file_path)와 Codex(apply_patch,
tool_input.patch의 "*** Add/Update File: ..." 마커) 두 이벤트 형식을 모두 처리한다.
"""

import json
import re
import sys
from pathlib import Path

# Windows 콘솔/파이프 기본 인코딩(cp949)은 한글 JSON 출력을 깨뜨린다. UTF-8로 고정.
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent.parent
TESTS_DIR = ROOT / "tests"

_PATCH_FILE_RE = re.compile(r"^\*\*\* (Add|Update|Delete) File: (.+)$", re.MULTILINE)


def _extract_paths(tool_input: dict) -> list:
    """Claude Code(file_path) / Codex apply_patch(patch 텍스트) 둘 다에서 대상 경로를 뽑는다."""
    file_path = tool_input.get("file_path")
    if file_path:
        return [file_path]
    patch = tool_input.get("patch")
    if patch:
        return [p for action, p in _PATCH_FILE_RE.findall(patch) if action != "Delete"]
    return []


def _missing_test_name(path_str: str):
    """path_str이 테스트가 필요한 src/ 구현 파일인데 테스트가 없으면 필요한 테스트 파일명을 반환한다."""
    path = Path(path_str)
    if path.suffix != ".py" or path.name == "__init__.py":
        return None

    parts = path.parts
    if "src" not in parts:
        return None  # scripts/, hooks 등 harness 계층은 이 가드 대상이 아니다
    if "tests" in parts or path.stem.startswith("test_"):
        return None  # 테스트 파일 자체는 항상 허용

    test_name = f"test_{path.stem}.py"
    if list(TESTS_DIR.rglob(test_name)):
        return None
    return test_name


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0

    tool_input = event.get("tool_input") or {}
    missing = [
        (p, name)
        for p in _extract_paths(tool_input)
        if (name := _missing_test_name(p))
    ]

    if not missing:
        return 0

    details = "; ".join(f"{p} → tests/{name} 없음" for p, name in missing)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"TDD GUARD: 구현 코드보다 테스트가 먼저 있어야 합니다 — {details}",
        }
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
