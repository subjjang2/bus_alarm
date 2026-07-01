#!/usr/bin/env python3
"""Codex Stop hook — 턴 종료 전 pytest를 돌려 실패 시 계속 진행하도록 지시한다.
Stop 이벤트는 exit 0 + stdout JSON을 요구한다 (평문 출력은 무효).
"""

import json
import subprocess
import sys

# Windows 콘솔/파이프 기본 인코딩(cp949)은 한글 JSON 출력을 깨뜨린다. UTF-8로 고정.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

MAX_REASON_CHARS = 4000


def main():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

    if result.returncode == 0:
        print(json.dumps({}))
        return 0

    reason = (result.stdout + result.stderr)[-MAX_REASON_CHARS:]
    print(json.dumps({
        "decision": "block",
        "reason": f"pytest tests/ 실패 — 아래 에러를 수정한 뒤 다시 종료를 시도하라:\n{reason}",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
