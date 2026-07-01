"""배포 전 기계적 점검 (predeploy 스킬 헬퍼).

pytest 통과 / 시크릿 노출 의심 패턴 / env 미커밋 / Procfile 존재를 확인한다.
하나라도 FAIL이면 exit 1.

사용법: python .claude/skills/predeploy/predeploy_check.py
"""

import re
import subprocess
import sys
from pathlib import Path

# Windows 콘솔/파이프 기본 인코딩(cp949)은 한글 출력을 깨뜨린다. UTF-8로 고정.
# (scripts/hooks/tdd_guard.py 와 동일한 패턴.)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

_ROOT = Path(__file__).resolve().parents[3]

# 하드코딩된 키/토큰 의심 패턴 (텔레그램 봇 토큰 형식, 흔한 변수명에 긴 리터럴 대입 등)
_HARDCODED_RE = re.compile(
    r"""(?xi)
    \d{6,}:[A-Za-z0-9_-]{30,}          # 텔레그램 봇 토큰 형식
    | (api_key|token|secret)\s*=\s*["'][A-Za-z0-9_-]{16,}["']  # 변수 = "긴 리터럴"
    """
)
# 예외를 str(exc)/{exc} 형태로 노출 — serviceKey/토큰이 담긴 요청 URL이 샐 수 있음
_EXC_LEAK_RE = re.compile(r"""(?x)
    str\(\s*exc\w*\s*\)     # str(exc), str(exc_info) 등
    | \{\s*exc\w*\s*\}      # f"{exc}" 안의 {exc}
    """)

_results = []


def check(name: str, ok: bool, detail: str = ""):
    _results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    line = f"[{status}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)


def check_pytest():
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/"],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    check("pytest tests/", proc.returncode == 0, tail)


def check_secret_scan():
    hits = []
    for py_file in (_ROOT / "src").rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _HARDCODED_RE.search(line):
                hits.append(f"{py_file.relative_to(_ROOT)}:{lineno}: 하드코딩 의심")
            if _EXC_LEAK_RE.search(line):
                hits.append(f"{py_file.relative_to(_ROOT)}:{lineno}: 예외 문자열 노출 의심")
    check("시크릿 노출 스캔 (src/)", not hits, "; ".join(hits) if hits else "이상 없음")


def check_env_not_tracked():
    proc = subprocess.run(
        ["git", "ls-files", "env/"], cwd=_ROOT, capture_output=True, text=True
    )
    tracked = proc.stdout.split()
    leaked = [f for f in tracked if f.endswith(".env")]
    check("env/.env 미커밋", not leaked, ", ".join(leaked) if leaked else "추적 안 됨(정상)")


def check_deploy_files():
    missing = [
        name
        for name in ("Procfile", "requirements.txt")
        if not (_ROOT / name).exists()
    ]
    check("Procfile/requirements.txt 존재", not missing, ", ".join(missing))


def main():
    check_pytest()
    check_secret_scan()
    check_env_not_tracked()
    check_deploy_files()

    failed = [name for name, ok, _ in _results if not ok]
    print()
    if failed:
        print(f"배포 보류: {len(failed)}개 항목 실패 — {', '.join(failed)}")
        sys.exit(1)
    print("모든 점검 통과. 배포를 진행할 수 있습니다.")


if __name__ == "__main__":
    main()
