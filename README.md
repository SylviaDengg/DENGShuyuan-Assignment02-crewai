# Source Credibility Heuristic Tool

## What this tool does
This project provides a lightweight Source Credibility Heuristic for AI-agent workflows. It outputs a rough trust score (`0-100`) for a single source record using simple signals:
- domain patterns (trusted/suspicious hints)
- byline/author presence
- clickbait phrase and excessive-capitalization signals

It is designed for first-pass ranking and triage, not factual verification.

## Files
- `tool.py`: core scorer and safe wrapper with structured error responses
- `demo.py`: agent-like workflow demo with success and bad-input cases
- `prompt-log.md`: assignment chat history log

## Run
```bash
python demo.py
```

Optional API-ready routing mode (no code changes required):

```bash
export USE_REAL_LLM_AGENT=1
export DEEPSEEK_API_KEY=your_key_here
python demo.py
```

When these environment variables are present, `demo.py` attempts real LLM-based tool routing and falls back to simulated routing on API errors.

## Design choices
- Deterministic heuristics keep behavior transparent and easy to evaluate.
- Core logic raises `ToolValidationError`; wrapper normalizes errors for robust workflow integration.
- Return payloads are JSON-serializable dictionaries for easy orchestration and logging.

## Limitations
- This score is not a truth detector and can be wrong.
- Domain heuristics can become stale and may encode bias.
- Clickbait/caps patterns are language- and style-dependent.
- High score does not guarantee accuracy; low score does not prove falsehood.
