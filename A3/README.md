# Graded Lab 3 — Validated Agent Pipelines

**Code Assignment 3 · CSI 4900 / CSI 5900 · Agentic AI**

Follow the numbered steps below for your first run. **You can complete all graded
work without an API key.** Installation needs internet access; the offline lab
does not. Use the Jupyter route unless you already use VS Code for notebooks.

## 1. Extract the student ZIP

On Windows, right-click the ZIP and choose **Extract All**. On macOS, double-click
the ZIP. Open the extracted folder, then the inner `Graded_Lab_3_Validated_Pipelines`
folder. Do not open the notebook while it is still inside the ZIP.

You should have these files together:

```text
Graded_Lab_3_Validated_Pipelines/
    Graded_Lab_3_Validated_Pipelines.ipynb
    lab_tools.py
    unittests.py
    requirements.txt
    README.md
    .env.example
```

`.env.example` may be hidden because its name begins with a dot; it is needed only
for live mode. Keep the notebook and both `.py` helpers in this same folder.

## 2. Prepare Python and install the packages

The lab requires Python 3.10 or newer; release checks used **Python 3.13**. If you
need Python, install Python 3.13 from [python.org](https://www.python.org/downloads/),
then close and reopen your terminal. If your course already provides a Python
environment, ask your TA before replacing it.

The following are **terminal commands**, not notebook-cell code. Choose the block
for your operating system. Run one line at a time and stop if a command fails.

### Windows — PowerShell

Open the extracted folder in File Explorer. Click its address bar, type
`powershell`, and press Enter. This opens PowerShell in that folder. Run:

```powershell
Get-Location
Get-ChildItem
py --version
```

Confirm the file list contains `requirements.txt` and the notebook. Confirm Python
is version 3.10 or newer. Then run:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m ipykernel install --prefix .\.venv --name lab3 --display-name "Python (Lab 3)"
.\.venv\Scripts\python.exe -m notebook
```

If `py` is unavailable but `python --version` reports a supported version, replace
`py` with `python` in the first two Python commands (`--version` and `-m venv`).
The remaining commands use the environment's own Python directly; you do not
need to activate it or change PowerShell's execution policy.

### macOS or Linux — Terminal

Open Terminal. Type `cd ` (including the space), drag the extracted lab folder
into the terminal, and press Enter; or use `cd "path/to/the/extracted/lab/folder"`
with your actual folder path. Run:

```bash
pwd
ls
python3 --version
```

Confirm that `requirements.txt` and the notebook are listed and Python is version
3.10 or newer. Then run:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m ipykernel install --prefix .venv --name lab3 --display-name "Python (Lab 3)"
./.venv/bin/python -m notebook
```

Package installation can take several minutes. `.venv` holds this lab's Python
environment; do not submit it. If installation reports an error, resolve it before
continuing. A pip update notice alone is not an installation failure.

## 3. Open the notebook and select its kernel

The last command starts Jupyter and usually opens a browser. Keep the terminal
open while working. If a browser does not open, copy the local Jupyter address
printed in that terminal into your browser; keep its login token private.

1. In Jupyter's file list, open `Graded_Lab_3_Validated_Pipelines.ipynb`.
2. Select **Python (Lab 3)** when asked for a kernel. If a different kernel is
   active, use **Kernel → Change Kernel** to select it. The kernel is the Python
   process that runs the cells; it must use the packages installed in Step 2.
3. Click a code cell and press **Shift+Enter** to run it and move to the next cell.
   Wait for a busy cell's `[*]` indicator to become an execution number.

If you need to verify the environment, insert a **temporary code cell** and run:

```python
import sys
from pathlib import Path
print(sys.executable)
print(Path.cwd())
print("Helpers present:", Path("lab_tools.py").exists(), Path("unittests.py").exists())
import aisuite
import dotenv
print("Package imports OK")
```

The Python path should contain `.venv`, both helper checks should be `True`, and
the final line should print `Package imports OK`. This cell does not use an API
key or call a model. Remove temporary diagnostic/setup cells before submission.

If you installed packages in the wrong environment, select the correct kernel.
For an existing course notebook environment, you can instead install into its
active kernel using this **temporary notebook cell**, then restart the kernel:

```python
%pip install -r requirements.txt
```

### If you prefer VS Code

Complete Step 2 through the package-installation command; you do not need to start
the browser-based Jupyter server. Install Microsoft's **Python** and **Jupyter**
extensions in VS Code. Use **File → Open Folder** to open the extracted lab folder,
then open the `.ipynb` file. Choose **Select Kernel → Python Environments** (possibly
under **Select Another Kernel**) and select this folder's `.venv` interpreter.
Run the temporary check above if you are unsure which interpreter is selected.
Use the cell run button or Shift+Enter, and **Run All** when instructed below.

## 4. Make your first offline run

1. In the setup cell, leave `RUN_LIVE = False`. You do not need a `.env` file yet.
2. Run from the top through Part A. The mode line should begin with `OFFLINE`.
   The complete book-exchange example should show `STATUS: complete`, followed by
   `Stricter gate: blocked`. This confirms the example can run in your environment.
3. Continue into Part B. Replace `...` only inside the marked exercise regions.
   Complete Exercise 1, then 2, then 3; their point values are 25, 40, and 35.
4. After editing a function, **run its definition cell again**, then run its test
   cell. Editing text alone does not update the function in the running kernel.
5. Run **Run all graded checks** after completing all three functions. The target
   is `TOTAL: 100/100`.
6. Run Part C. A completed solution shows `STATUS: complete`, approved records
   `RC-11`, `RC-12`, `RC-13`, and a report. In offline mode, the three counted
   model calls are calls to the scripted client, not requests to an online API.
7. Part D is optional. It should show a passing 0.6 threshold and a blocked 0.8
   threshold, with no additional online calls.

**Expected starter behavior:** before you fill the exercises, tests report failed
checks (the untouched starter earns 15/100 from supplied protections), and Part C
is skipped. This is normal, not an installation problem. `Ellipsis` in test
feedback usually means an exercise still contains `...`.

Only edit marked exercise regions and `RUN_LIVE`; do not edit the helpers or tests.

All graded tests run offline. Offline planner/writer/editor replies are fixed
teaching examples, not language-model outputs. Retrieval uses a fictional local
collection. Its `.example` URLs are labels, not websites to visit. No search API,
web browsing, or paid account is required.

## 5. Optional: run with the real Gemini API

Complete Part B successfully first. Then:

1. Open [Google AI Studio's API key page](https://aistudio.google.com/apikey), sign
   in, and create or select an API key for a project with available free API access.
   Check that project's model access and [limits](https://aistudio.google.com/rate-limit).
   Do not enable paid usage or purchase credits for this assignment.
2. In the extracted lab folder, copy `.env.example` to a new file named exactly
   `.env`. Keep the original template. From a terminal in that folder, use:

   Windows PowerShell:

   ```powershell
   Copy-Item -LiteralPath .env.example -Destination .env
   ```

   macOS/Linux Terminal:

   ```bash
   cp .env.example .env
   ```

   Do this only when you do not already have a configured `.env` file.
3. Open `.env` in a plain-text editor. Paste the key **after** `GEMINI_API_KEY=`
   on its first line, without adding spaces or quotes. Leave these other lines:

   ```text
   GEMINI_MODEL=openai:gemini-3.5-flash-lite
   MIN_CALL_INTERVAL=5
   ```

   Save the file beside `lab_tools.py`. Ensure its name is `.env`, not `.env.txt`;
   enable file-name extensions in your file browser if necessary. Do not paste the
   key into a notebook cell, a screenshot, a chat message, or the template.
4. Change the notebook's switch to `RUN_LIVE = True`.
5. Use **Kernel → Restart Kernel and Run All Cells** in Jupyter, or restart the
   kernel and click **Run All** in VS Code. Restarting matters after `.env` changes.
6. The mode line should now say `LIVE Gemini via aisuite`. If the API succeeds,
   Parts A and C show model-generated reports; wording can differ on every run.

The actual model client is `aisuite.Client`. It sends requests to Google's
OpenAI-compatible endpoint using a Gemini key. The default model identifier is
`openai:gemini-3.5-flash-lite`; `openai:` selects the interface, not an OpenAI
account. A bare Gemini model name also works. Override `GEMINI_MODEL` in `.env`
if your TA recommends a different accessible model, then restart the kernel.

A successful run of Parts A and C makes six model calls. Calls are paced with a
five-second minimum interval and have no automatic retries. Pacing does not
guarantee quota. The free tier depends on account/project availability; do not
purchase credits for this lab. If API access fails, use offline mode and add a
brief Markdown note. Your programming grade is unaffected by API access.

No live Gemini request was verified during release preparation. Offline execution
and client wiring were checked; model access still depends on your project.

## 6. Save, close, and reopen your work

Save often with **Ctrl+S** (Windows/Linux) or **Cmd+S** (macOS). Before finishing,
restart the kernel and run all cells from the top. If you cannot run live, return
to `RUN_LIVE=False`, restart/run all, and add the short access note.

To stop a browser-based Jupyter session, save the notebook, then press Ctrl+C in
the terminal that started Jupyter and confirm shutdown if prompted. Next time,
open a terminal in the same lab folder and run only the launch command:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m notebook
```

macOS/Linux Terminal:

```bash
./.venv/bin/python -m notebook
```

You normally do not need to recreate the environment or reinstall packages each
session. In VS Code, reopen the folder/notebook and select the same kernel.

## Troubleshooting

| What you see | What to check or do |
|---|---|
| `py` / `python3` not found | Install a supported Python, reopen the terminal, and check its version. Contact your TA if installation is restricted. |
| `requirements.txt` not found | You are in the wrong folder. Use `Get-ChildItem` or `ls`; enter the folder that contains the notebook and requirements file. |
| `venv` / `ensurepip` unavailable on Linux | Ask your TA or lab administrator to provide the Python venv component for that machine. |
| Jupyter opens an empty/wrong folder | Stop it and rerun the launch command from the extracted lab folder. |
| Missing `aisuite`, `dotenv`, or `mcp` | Select the environment where you installed the requirements, or run `%pip install -r requirements.txt` in a temporary cell and restart. |
| Missing `lab_tools` or `unittests` | Extract all files and keep both helpers beside the notebook; check the working folder with the diagnostic cell in Step 3. |
| Changes seem to have no effect / `NameError` | Rerun the function definition cell, or restart the kernel and run from the top. |
| Tests fail with `Ellipsis` / Part C skipped | Complete the marked `...` regions and rerun definitions/tests. This is expected in the starter. |
| Missing `GEMINI_API_KEY` | Check `.env` is beside `lab_tools.py`, its name has no `.txt` suffix, and the key field is filled; restart the kernel. Do not print the key. |
| API 401/403 | Check the key, project, and account access; contact your TA without sharing the key. |
| API 404 | Check model access and ask your TA which `GEMINI_MODEL` to use, then restart. |
| API 429 | Inspect project limits and wait for the relevant reset; rapidly retrying does not resolve daily quota. Use offline mode meanwhile. |
| JSON/plan validation error in live mode | Keep the supplied format/parser; retry manually if quota permits. If it persists, use offline mode and contact your TA. |

When requesting help, provide the error text and which step failed. Remove any
credentials or Jupyter login tokens before sharing terminal output.

## Optional alternative: Google Colab

Local Jupyter/VS Code is the primary route; Colab was not separately tested for
this release. In Colab, upload the `.ipynb` using **File → Upload notebook**, then
upload `lab_tools.py`, `unittests.py`, and `requirements.txt` using the runtime's
Files panel. Put them in the runtime working folder, not only in Google Drive.
Add a temporary first code cell with `%pip install -r requirements.txt` and run it.
Then follow Step 4 with `RUN_LIVE=False`.

For optional live mode, create a Colab Secret named `GEMINI_API_KEY`, grant the
notebook access, and use this temporary setup cell before the lab's setup cell:

```python
import os
from google.colab import userdata
os.environ["GEMINI_API_KEY"] = userdata.get("GEMINI_API_KEY")
```

Do not write the literal key into code. A new runtime may require reuploading the
helper files and rerunning setup. Before submitting, switch to offline mode if
needed, remove the temporary setup cells, and run the original notebook cells
in order in the prepared runtime. Download the completed `.ipynb` from Colab's
File menu; do not submit just a Colab sharing link.

## Submit

Restart/run all, keep outputs, and save. Submit **only
`Graded_Lab_3_Validated_Pipelines.ipynb`**. Do not submit `.env`, helpers, HTML, ZIP,
screenshots, or a separate report. Your instructor grades the three function
definitions with original helpers; extra cells cannot be solution dependencies.
Live writing quality and Part D observations are not graded.

Technical references: [AISuite](https://github.com/andrewyng/aisuite),
[Gemini compatibility](https://ai.google.dev/gemini-api/docs/openai),
[model details](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite),
[pricing](https://ai.google.dev/gemini-api/docs/pricing),
[Python environments](https://docs.python.org/3/library/venv.html),
[starting Jupyter](https://docs.jupyter.org/en/latest/running.html),
[VS Code notebooks](https://code.visualstudio.com/docs/datascience/jupyter-notebooks).
