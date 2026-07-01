#!/usr/bin/env python3
"""Codex PreToolUse hook — Bash 도구 호출 전 위험한 명령어를 차단한다.
stdin으로 hook 이벤트 JSON을 받아 tool_input.command를 검사한다.
"""

import json
import re
import sys

# Windows 콘솔/파이프 기본 인코딩(cp949)은 한글 JSON 출력을 깨뜨린다. UTF-8로 고정.
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

DANGEROUS_PATTERN = re.compile(
    r"rm\s+-rf|git\s+push\s+--force|git\s+reset\s+--hard|DROP\s+TABLE",
    re.IGNORECASE,
)


def main():
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0

    command = event.get("tool_input", {}).get("command", "")
    if not DANGEROUS_PATTERN.search(command):
        return 0

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "BLOCKED: 위험한 명령어가 감지되었습니다.",
        }
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
