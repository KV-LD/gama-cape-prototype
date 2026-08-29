# GAMA CAPE prototype

G.A.Menon Academy — Capability Assessment & Proficiency Engine (FDE track).

You can run this as a **web app** (recommended, deployable on [Netlify](https://www.netlify.com/)) or as the original **command-line** tool. In both cases the scored attempt is saved to GitHub as JSON **and** as a formatted HTML report.

## Why `npm install` failed

`npm error ENOENT ... package.json` means you are not in the folder that contains the web app files.

That happens if you downloaded a **zip of `main`**. The live GitHub `main` branch is still the Python CLI only, so it has no `package.json`. The web app lives on branch `cursor/cape-web-ui-a7cc` (pull request #2).

It also happens if GitHub unzipped into a nested folder, for example:

`Documents\GitHub\gama-cape-prototype-main\gama-cape-prototype-main`

That inner folder of `main` has `main.py` and `README.md`, but not `package.json`.

### Get the web app onto your PC (Windows)

1. Install [Git](https://git-scm.com/download/win) and [Node.js LTS](https://nodejs.org/) if they are not already installed. Close and reopen Command Prompt after installing.
2. In Command Prompt:

```
cd %USERPROFILE%\Documents\GitHub
git clone https://github.com/KV-LD/gama-cape-prototype.git
cd gama-cape-prototype
git checkout cursor/cape-web-ui-a7cc
dir package.json
```

You must see `package.json` listed. Then:

```
npm install
npm run dev
```

Open http://localhost:3000

If `dir package.json` says file not found, you are still on `main` or in the wrong folder. Run `git branch` and `cd` until you are in the repo root that contains `package.json`.

## Deploy to Netlify (step by step)

Do this **after** the web-app branch is in GitHub (it already is: `cursor/cape-web-ui-a7cc`). You can deploy that branch now, or merge PR #2 into `main` first and then deploy `main`.

### A. Put the secrets in Netlify (required for generating a capstone and scoring)

You need the same two keys as the CLI:

- `OPENROUTER_API_KEY` from https://openrouter.ai/keys
- `GITHUB_TOKEN` from https://github.com/settings/tokens (classic token with `repo` scope, or a fine-grained token with Contents: Read and write on `KV-LD/gama-cape-prototype`)

Optional:

- `GITHUB_REPO` — defaults to `KV-LD/gama-cape-prototype`
- `GITHUB_ATTEMPTS_BRANCH` — defaults to `main`

You will paste these into Netlify in step 8 below. Do not commit them into Git.

### B. Create the Netlify site from GitHub

1. Open https://app.netlify.com and sign in (GitHub login is easiest).
2. Click **Add new site** → **Import an existing project**.
3. Choose **GitHub**. Authorize Netlify if it asks, and grant access to `KV-LD/gama-cape-prototype` (for a private repo, click **Configure Netlify on GitHub** and enable that repository).
4. Select **KV-LD/gama-cape-prototype**.
5. Set **Branch to deploy** to `cursor/cape-web-ui-a7cc` until that branch is merged. After merge, switch this to `main`.
6. Build settings (these also live in `netlify.toml`, so you can leave Netlify’s form blank if it already detected Next.js):
   - Build command: `npm run build`
   - Publish directory: `.next`
7. Click **Add environment variables** (or after the first deploy: **Site configuration** → **Environment variables**) and add:

   | Key | Value |
   | --- | --- |
   | `OPENROUTER_API_KEY` | your OpenRouter key |
   | `GITHUB_TOKEN` | your GitHub token |
   | `GITHUB_REPO` | `KV-LD/gama-cape-prototype` |

   Scopes: **Production**, **Preview**, and **Local development** if you use Netlify Dev.

8. Click **Deploy KV-LD/gama-cape-prototype**.
9. Wait until the deploy is **Published**. Open the site URL (something like `https://something.netlify.app`).
10. Check it:
    - `/` should show the assessment wizard.
    - `/report` should convert a `record.json` file to HTML (this does not need the API keys).
    - **Generate capstone** needs `OPENROUTER_API_KEY`. Scoring also needs `GITHUB_TOKEN`.

If the site 404s or the build log says it cannot find `package.json`, the deployed branch is still CLI-only `main`. Point the Netlify branch at `cursor/cape-web-ui-a7cc`.

### Timeouts on Netlify

Capstone generation and scoring call Grok and can take 20–60 seconds. Netlify often stops a function after **10 seconds** (free) or a bit longer on paid plans. If **Generate capstone** or scoring fails with a timeout, keep using the Python CLI (`python main.py`) for those long steps. The wizard UI and JSON → HTML report still work on the free tier.

### Redeploy after you change code

Push to the branch Netlify is watching. It will rebuild automatically.

```
git add -A
git commit -m "Your message"
git push
```

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

Convert an existing `record.json` without the website:

```
python report.py attempts\KV_2_20260826T180319Z\record.json
```

## What the verdicts mean

- **EXEMPTED** — blended score at least 75, and no skill or VECTOR dimension below 50
- **COMPLETION PASS — TRAINING RECOMMENDED, NOT EXEMPTED** — blended score at least 50, but not exemption
- **FAIL — FULL TRAINING REQUIRED** — blended score below 50
- **BORDERLINE — HUMAN REVIEW REQUIRED** — the two scoring passes disagreed by more than 25 points on any item (this overrides the numeric score)

Final blended score = (module skill average × 0.6) + (VECTOR average × 0.4).
