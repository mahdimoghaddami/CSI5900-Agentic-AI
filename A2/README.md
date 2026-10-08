# Graded Lab 2 — Tool Use

Open `Graded_Lab_2_Tool_Use.ipynb` in Jupyter or VS Code. Extract this whole folder
first: the notebook imports `lab_tools.py` and `unittests.py` from beside it.

## Install and start

Use Python 3.10 or newer (validated with Python 3.13). In your notebook's kernel:

```python
%pip install -r requirements.txt
```

The notebook starts with `RUN_LIVE=False`. Part A uses clearly labelled fixed
responses; all graded tests run offline. Complete Part B before switching modes.
Do not edit either helper file. Only change marked exercise regions and the
`RUN_LIVE` / `RUN_COMPARISON` switches.

## Enable the live model

1. Get a Gemini key from [Google AI Studio](https://aistudio.google.com/apikey).
   Use a project with an available free tier. You do not need an OpenAI key.
2. Copy `.env.example` to `.env` beside the notebook.
3. Set `GEMINI_API_KEY` in `.env`. Keep it out of notebook cells and outputs.
4. Set `RUN_LIVE=True`, restart the kernel, and run all cells.

Default model: `openai:gemini-3.5-flash-lite`. If unavailable, consult your TA and
set `GEMINI_MODEL` in `.env` to an available free model supporting tool calls and
JSON output. Restart the kernel after changing it. This lab uses `aisuite` with
Google's OpenAI-compatible endpoint. The `openai:` prefix selects the compatible
interface; requests still go to Google using your Gemini key. The helper also
accepts a bare Gemini model name and adds this prefix automatically.

The model client waits five seconds between attempts and does not retry
automatically. This reduces request bursts but cannot guarantee quota access.
Check [your project limits](https://aistudio.google.com/rate-limit). For 429 errors,
pause and check whether a per-minute or daily limit was reached. If daily quota
is exhausted or your account cannot access the API, use offline mode and add a
brief note in the notebook. This does not reduce your programming grade. Do not
purchase credits for this assignment.

For Google Colab, upload the notebook, `lab_tools.py`, and `unittests.py` to the
runtime. Install `aisuite[openai,mcp]==0.2.0` and `python-dotenv` in a temporary setup cell. Use Colab
Secrets to set `GEMINI_API_KEY` in the runtime environment; do not type the key
into a saved cell. Local Jupyter/VS Code is the primary validated route.

## Submit

Restart and run all cells, keep the outputs, and save. Submit **only
`Graded_Lab_2_Tool_Use.ipynb`**. No `.env`, `.py`, HTML, ZIP, screenshots, or separate
report. API-dependent outputs and the optional budget comparison are not graded.

Your instructor reruns the three function definitions using the original
helpers, so extra cells or edited test files cannot be dependencies of your solution.
