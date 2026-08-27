# GAMA CAPE prototype

G.A.Menon Academy — Capability Assessment & Proficiency Engine (FDE track).

You can run this as a **web app** (recommended, deployable on Vercel) or as the original **command-line** tool. In both cases the scored attempt is saved to GitHub as JSON **and** as a formatted HTML report.

## Web UI (Vercel)

1. Import this GitHub repo into [Vercel](https://vercel.com/new).
2. Framework preset: **Next.js**. Root directory: repository root.
3. Add environment variables (same secrets as `.env`):

- `OPENROUTER_API_KEY`
- `GITHUB_TOKEN` (must be able to read and write `KV-LD/gama-cape-prototype`)
- `GITHUB_REPO` (optional, defaults to `KV-LD/gama-cape-prototype`)

4. Deploy. Open the site, fill in your profile, generate a capstone, paste your work, answer the defense questions, and wait for scoring.

Scoring uses two independent LLM passes, so each step can take up to about a minute. On Vercel Hobby the function timeout is 10 seconds, which is usually too short. Use **Vercel Pro** (or set function duration to 60 seconds) so generate / defense / scoring can finish.

Local web preview:

```
npm install
npm run dev
```

Then open http://localhost:3000

Convert an existing `record.json` to HTML in the browser at `/report`, or from the command line:

```
python report.py attempts/KV_2_20260826T180319Z/record.json
```

That writes `report.html` next to the JSON file. New attempts also commit `report.html` to GitHub automatically.

## Command-line tool

You do not need to write code. You answer questions, paste your work, and it saves a scored record to GitHub.

### First-time setup (do this once)

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

### Run an assessment

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

After 2–3 follow-up questions it prints a scoring sheet and saves the full record under `attempts/` in this GitHub repo (`record.json` plus `report.html`).

## What the verdicts mean

- **EXEMPTED** — blended score at least 75, and no skill or VECTOR dimension below 50
- **COMPLETION PASS — TRAINING RECOMMENDED, NOT EXEMPTED** — blended score at least 50, but not exemption
- **FAIL — FULL TRAINING REQUIRED** — blended score below 50
- **BORDERLINE — HUMAN REVIEW REQUIRED** — the two scoring passes disagreed by more than 25 points on any item (this overrides the numeric score)

Final blended score = (module skill average × 0.6) + (VECTOR average × 0.4).
