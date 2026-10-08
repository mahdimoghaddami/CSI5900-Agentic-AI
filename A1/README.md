# Graded_Lab_1_Reflection


## What you got

```
Graded_Lab_1_Reflection.ipynb   the lab — this is the only file you submit
utils.py                         helpers and the rule checker (do not edit)
unittests.py                     the offline tests (do not edit)
requirements.txt                 dependencies
.env.example                     template for your API key
```

## Setup (about five minutes)

**1. Install the dependencies.**

```bash
pip install -r requirements.txt
```

A virtual environment is recommended but not required:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**2. Get a free API key.**

Go to <https://aistudio.google.com/apikey>, sign in with any Google account, and
click **Create API key**. It is free and does not ask for a credit card.

**3. Put the key where the notebook can find it.**

```bash
cp .env.example .env
```

Open `.env` and paste your key after `GEMINI_API_KEY=`. Save it.

**4. Start Jupyter and open the notebook.**

```bash
jupyter notebook
```

Run the setup cell. If it prints `client ready`, you are done.

## Working on the assignment

The three exercises are **your whole grade**, and they are checked by
`unittests.py`, which runs **offline against a fake model**. Running the tests
costs you nothing and needs no key, so debug there first and only run the live
cells (Parts A, C and D) when your tests pass.

Parts C and D are not graded. They chain your three functions together so you can
watch your own agent work and see what reflection bought. Run them and look at the
output; whatever the numbers are, they do not affect your score.

A full run of the whole notebook costs about 21 requests. The free tier gives
this model 500 per day, so you can run the whole thing around twenty times. If you do hit a limit,
wait a minute and re-run the cell — `get_client()` already spaces calls out for
you.

## When something breaks

**`GEMINI_API_KEY is not set`** — the `.env` file is missing, is not in the same
folder as the notebook, or the key was pasted on the wrong line. After editing
`.env`, restart the kernel; `load_dotenv()` only reads the file once.

**`404` or `model not found`** — Google has retired that model id. Open
<https://ai.google.dev/gemini-api/docs/models>, pick a current **Flash-Lite**
model, and change `DRAFT_MODEL` / `CRITIC_MODEL` at the top of `utils.py`. Tell
the instructor, because it affects everybody at once. (As of September 2026 the
`gemini-2.5-*` ids are already gone for new accounts.)

**`429` or `You exceeded your current quota`** — you ran out of requests. Open
<https://aistudio.google.com/rate-limit> to see your live numbers. The model this
lab uses allows 15 requests per minute and 500 per day, and a full run of the
notebook is about 21 requests, so hitting the daily cap takes real effort. If you
hit the *per-minute* limit, wait sixty seconds and re-run the cell — and do not
run two copies of Part D at the same time. If you changed the model ids yourself,
change them back: some models have a much smaller free allowance.

**A test says `made 0 model call(s)`** — your function never called the model, or
it returned text you wrote yourself. Keep `client = client or get_client()` as the
first line and return `response.choices[0].message.content`.

**A test says the prompt is missing banned terms** — you described the rules in
your own words and left some out. Put `{task.rules_text()}` inside your f-string
instead; it expands to all four rules, already written out.

**The score goes *down* after a revision** — your reviser is returning "Here is
the revised summary: ..." and the wrapper sentence counts toward the word limit.
Tell it to return the summary and nothing else.

## Rules

Do not edit `utils.py` or `unittests.py`. Do not hard-code summaries — every
function must get its text from the model, and the tests check for this.
Discussing the lab with classmates is fine; submitting shared code is not.

Never put anything confidential into a prompt. Free-tier traffic may be used by
the provider to improve its products, so treat every prompt as public.

## Submitting

Restart the kernel, run all cells in order, confirm the tests print `3/3`, and
upload **only** `Graded_Lab_1_Reflection.ipynb` during the quiz.
