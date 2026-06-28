from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from genshin_lore_db.search_engine.local_llm import DEFAULT_OLLAMA_MODEL, ensure_ollama_server, find_ollama_executable, strip_thinking_blocks


def main() -> int:
    parser = argparse.ArgumentParser(description="Install/check Ollama and pull the default local QA model.")
    parser.add_argument("--install", action="store_true", help="Install Ollama with winget when ollama is missing.")
    parser.add_argument("--model", default=DEFAULT_OLLAMA_MODEL)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    steps: list[dict[str, Any]] = []
    ollama = find_ollama_executable()
    if not ollama:
        if not args.install:
            return finish(
                steps,
                ok=False,
                message="ollama executable was not found. Run with --install or install Ollama manually.",
            )
        install_result = install_ollama()
        steps.append(install_result)
        if not install_result["ok"]:
            return finish(steps, ok=False, message="Ollama installation failed.")
        ollama = find_ollama_executable()
        if not ollama:
            return finish(
                steps,
                ok=False,
                message="Ollama was installed but the executable was not found in PATH. Open a new terminal and retry.",
            )

    steps.append({"step": "find_ollama", "ok": True, "path": ollama})
    serve_result = ensure_ollama_server(ollama, timeout=args.timeout)
    steps.append(serve_result)
    pull_result = run_command([ollama, "pull", args.model], step="pull_model", timeout=args.timeout)
    steps.append(pull_result)
    if not pull_result["ok"]:
        return finish(steps, ok=False, message=f"Failed to pull model {args.model}.")

    list_result = run_command([ollama, "list"], step="list_models", timeout=60)
    steps.append(list_result)
    chat_result = test_chat(args.model, timeout=60)
    steps.append(chat_result)
    return finish(steps, ok=chat_result["ok"], message="Local QA model setup complete." if chat_result["ok"] else "Chat test failed.")

def install_ollama() -> dict[str, Any]:
    winget = shutil.which("winget")
    if not winget:
        return {"step": "install_ollama", "ok": False, "error": "winget was not found."}
    return run_command(
        [
            winget,
            "install",
            "-e",
            "--id",
            "Ollama.Ollama",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ],
        step="install_ollama",
        timeout=600,
    )

def test_chat(model: str, *, timeout: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "stream": False,
        "think": False,
        "messages": [
            {"role": "user", "content": "/no_think\n한국어로 '준비 완료'만 말해."},
        ],
        "options": {"temperature": 0.1},
    }
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"step": "chat_test", "ok": False, "error": str(exc)}
    content = strip_thinking_blocks(str((data.get("message") or {}).get("content") or "")).strip()
    return {
        "step": "chat_test",
        "ok": bool(content),
        "content": content,
    }


def run_command(command: list[str], *, step: str, timeout: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        return {"step": step, "ok": False, "command": command, "error": str(exc)}
    return {
        "step": step,
        "ok": completed.returncode == 0,
        "command": command,
        "returncode": completed.returncode,
        "stdout": (completed.stdout or "")[-4000:],
        "stderr": (completed.stderr or "")[-4000:],
    }


def finish(steps: list[dict[str, Any]], *, ok: bool, message: str) -> int:
    result = {
        "ok": ok,
        "message": message,
        "manual_next_steps": [] if ok else manual_next_steps(),
        "steps": steps,
    }
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0 if ok else 1


def manual_next_steps() -> list[str]:
    return [
        "Install Ollama from https://ollama.com/download or with winget install -e --id Ollama.Ollama.",
        f"Run: ollama pull {DEFAULT_OLLAMA_MODEL}",
        f"Retry: python scripts/setup_local_llm.py --model {DEFAULT_OLLAMA_MODEL}",
    ]


if __name__ == "__main__":
    raise SystemExit(main())
