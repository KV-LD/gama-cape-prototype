# GAMA CAPE prototype

G.A.Menon Academy — Capability Assessment & Proficiency Engine (FDE track).

This is a command-line tool. You do not need to write code. You answer questions, paste your work, and it saves a scored record to GitHub.

## First-time setup (do this once)

1. Install Python 3 on your computer if it is not already installed.
2. Open a terminal in this folder.
3. Install the two small libraries:

```
pip install -r requirements.txt
```

4. Copy the example secrets file:

```
copy .env.example .env
```

On a Mac or Linux machine use `cp .env.example .env` instead of `copy`.

5. Open the new `.env` file in any text editor and paste your real keys:

- `OPENROUTER_API_KEY` from https://openrouter.ai/keys
- `GITHUB_TOKEN` from https://github.com/settings/tokens (it must be able to read and write the `KV-LD/gama-cape-prototype` repo)

6. Check that everything works **before** you run a real attempt:

```
python check_env.py
```

You want every line to say PASS. If something says FAIL, follow the sentence under it — do not run `python main.py` until this check is clean.

## Run an assessment

```
python main.py
```

You will be asked, one at a time:

1. Your name
2. Domain (healthcare / retail / bfsi / manufacturing / supply chain / automotive)
3. Which of the 9 FDE modules
4. Which AI tools you used
5. Which cloud you used (or None)

Then the tool writes a fresh capstone problem. Paste your written notes, type `END` on its own line, then paste your code and type `END` again. You can also type a file path instead of pasting.

After 2–3 follow-up questions it prints a scoring sheet and saves the full record under `attempts/` in this GitHub repo.

## What the verdicts mean

- **EXEMPTED** — blended score at least 75, and no skill or VECTOR dimension below 50
- **COMPLETION PASS — TRAINING RECOMMENDED, NOT EXEMPTED** — blended score at least 50, but not exemption
- **FAIL — FULL TRAINING REQUIRED** — blended score below 50
- **BORDERLINE — HUMAN REVIEW REQUIRED** — the two scoring passes disagreed by more than 25 points on any item (this overrides the numeric score)

Final blended score = (module skill average × 0.6) + (VECTOR average × 0.4).
