"""Client for local Ollama Qwen3-4B model with robust error handling and timeout fallbacks."""

import os
import json
import re
import socket
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse
from typing import Any, Dict, Optional


OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_API_URL = f"{OLLAMA_HOST}/api/generate"
OLLAMA_TAGS_URL = f"{OLLAMA_HOST}/api/tags"
PRIMARY_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b")

_OLLAMA_STATUS_CACHE: Dict[str, Any] = {"status": None, "timestamp": 0.0}


def strip_internal_reasoning(text: str) -> str:
    """
    Thoroughly strip internal chain-of-thought, planning text, thinking tags,
    and conversational preambles (e.g. 'Okay, the user wants me to...').
    Guarantees that only the final scientific answer is returned.
    """
    if not text:
        return ""

    # 1. Strip XML / bracketed thinking tags
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    if "</thought>" in text:
        text = text.split("</thought>", 1)[1]
    if "</reasoning>" in text:
        text = text.split("</reasoning>", 1)[1]
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<reasoning>.*?</reasoning>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"\[THINK\].*?\[/THINK\]", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"\[REASONING\].*?\[/REASONING\]", "", text, flags=re.DOTALL | re.IGNORECASE)

    # 2. Check for leading unclosed thinking tag
    if text.strip().startswith("<think>") or text.strip().startswith("<thought>"):
        m_start = re.search(r"(?:###|\*\*Direct Answer\*\*|Direct Answer:)", text, re.IGNORECASE)
        if m_start:
            text = text[m_start.start():]
        else:
            text = re.sub(r"^<think>.*?(?=\n\n)", "", text, flags=re.DOTALL | re.IGNORECASE)

    # 3. Strip natural-language planning preambles and chain-of-thought lines
    lines = text.split("\n")
    cleaned_lines = []
    in_planning_preamble = True

    planning_indicators = (
        "okay, the user wants",
        "okay, i need to",
        "okay, let's",
        "the user wants me to",
        "the user is asking for",
        "the user asks",
        "thinking process:",
        "thought process:",
        "internal reasoning:",
        "reasoning process:",
        "my plan:",
        "plan:",
        "first, let's",
        "first, i will",
        "first, i need to",
        "let's analyze",
        "let's break down",
        "let's examine",
        "to answer this question, i should",
        "i need to compare",
        "here is my plan",
        "analysis of the query:",
    )

    for line in lines:
        stripped = line.strip()
        lower_line = stripped.lower()

        if in_planning_preamble:
            # Check if this line is an internal reasoning indicator
            if any(lower_line.startswith(p) for p in planning_indicators):
                continue
            # Check if line looks like planning bullet: e.g. "1. Analyze dopants...", "2. Check literature..."
            if re.match(r"^\d+\.\s*(?:analyze|examine|look at|review|check|retrieve|compare|filter)\b", lower_line):
                continue
            # If we hit an actual scientific header or non-planning text
            if stripped.startswith("###") or stripped.startswith("**Direct Answer") or stripped.startswith("Direct Answer:"):
                in_planning_preamble = False
                cleaned_lines.append(line)
            elif stripped:
                if not any(lower_line.startswith(p) for p in planning_indicators):
                    in_planning_preamble = False
                    cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)

    text = "\n".join(cleaned_lines).strip()

    # 4. If any leading "Okay, the user wants me to..." block remains, strip via regex
    text = re.sub(
        r"^(?:Okay,\s*)?(?:the user wants me to|I need to analyze|Let's examine the retrieved).*?(?=\n\n|\n###|\n\*\*|$)",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    return text.strip()


def strip_thinking_tokens(text: str) -> str:
    """Backward-compatible alias for strip_internal_reasoning."""
    return strip_internal_reasoning(text)


def check_ollama_status(timeout_s: float = 0.5, cache_ttl_s: float = 5.0) -> bool:
    """Check whether local Ollama service is reachable and responsive."""
    now = time.time()
    if _OLLAMA_STATUS_CACHE["status"] is not None and (now - _OLLAMA_STATUS_CACHE["timestamp"]) < cache_ttl_s:
        return bool(_OLLAMA_STATUS_CACHE["status"])

    status = False
    try:
        parsed = urlparse(OLLAMA_HOST)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80 if parsed.scheme == "http" else 11434)
        with socket.create_connection((host, port), timeout=timeout_s):
            pass
        req = urllib.request.Request(OLLAMA_TAGS_URL, headers={"User-Agent": "HE-LMFP-Copilot"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = (resp.status == 200)
    except Exception:
        status = False

    _OLLAMA_STATUS_CACHE["status"] = status
    _OLLAMA_STATUS_CACHE["timestamp"] = now
    return status


def call_qwen_model(
    prompt: str,
    system_prompt: Optional[str] = None,
    timeout_s: float = 90.0,
    model_name: str = PRIMARY_MODEL,
) -> Optional[str]:
    """
    Send prompt to local Qwen3-4B via Ollama.
    Returns clean response text or None if Ollama is unreachable/timed out.
    """
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.1,  # Low temperature for strict scientific fidelity
            "top_p": 0.9,
            "num_predict": 1024,
        },
    }
    if system_prompt:
        payload["system"] = system_prompt

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_API_URL,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "HE-LMFP-Copilot"},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            raw = res.get("response", "")
            return strip_thinking_tokens(raw)
    except Exception as exc:
        print(f"[Copilot LLM Client] Ollama inference failed/timed out: {exc}")
        return None
