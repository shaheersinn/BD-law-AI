# SKILL: Git Workflow & CI/CD Safety
## For ORACLE BD Intelligence Platform

> Read this entire file before running any `git` command.
> The CD pipeline deploys directly to production on DigitalOcean App Platform.
> A bad push to `main` triggers a live deploy. There is no staging gate.

---

## 1. The Two Pipelines — Know Which One You're Touching

| Pipeline | File | Trigger | What It Does |
|---|---|---|---|
| **CI** | `.github/workflows/ci.yml` | Every push to any branch + PRs to main | Ruff lint, mypy, Bandit security scan, Pytest |
| **CD** | `.github/workflows/cd.yml` | Push to `main` ONLY | Re-runs CI, then builds Docker image, deploys to DO App Platform, smoke tests |

**CD deploys to production automatically.** There is no manual approval step.
Pushing broken code to `main` = broken production for real users.

---

## 2. Branch Strategy

### Never push design/UI work directly to `main`

Always work on a feature branch:

```bash
# Naming convention: feat/short-description
git checkout -b feat/digital-atelier-design-system
git checkout -b feat/landing-page
git checkout -b feat/stitch-dashboard-integration
```

### When to merge to main
Only after:
1. All local pre-commit checks pass (see Section 5)
2. CI passes on the feature branch (check GitHub Actions tab)
3. `npm run build` produces no errors
4. You have manually verified the UI renders in a browser (`npm run dev`)

---

## 3. What the CI Pipeline Checks (and Will Fail On)

CI runs against `backend/` — it does NOT lint the frontend directly. However:
- A broken `frontend/` build will cause the CD Docker build to fail
- Ruff, mypy, and Bandit run against `backend/app/` and `backend/tests/`
- **You must not modify any backend files.** Frontend only.

CI steps that will block your PR:
```
ruff check app/ tests/          ← Python lint
ruff format --check app/        ← Python formatting
mypy app/ --ignore-missing-imports
bandit -r app/ -ll -q
pytest tests/ -x -q --tb=short --ignore=tests/load --ignore=tests/integration
```

If CI fails on your branch for reasons unrelated to your changes (pre-existing
backend failures), document this in your commit message and do not attempt to fix
backend issues — that's out of scope for frontend work.

---

## 4. What the CD Pipeline Does (Read This Carefully)

When code lands on `main`, CD:
1. Runs the full CI suite again as a gate
2. Builds and pushes the backend Docker image to DigitalOcean Container Registry:
   `registry.digitalocean.com/oracle-containers/oracle-backend:latest`
3. Updates the DO App spec via `doctl apps update` using `do-app.yaml`
4. Waits for deployment phase to be `ACTIVE`
5. Smoke tests: `GET /api/health` and `GET /api/v1/scores/top-velocity`
6. On failure: posts a Slack alert to `SLACK_WEBHOOK_URL`

**The frontend is deployed via Vercel**, not Docker. Vercel picks up the `frontend/`
directory on pushes to `main` automatically. No additional config needed.

**NEVER run `alembic upgrade head` in your scripts or commits.**
DB migrations are manual via `scripts/run_migrations.sh`. The CD pipeline explicitly
documents this: "NEVER runs alembic upgrade head — migrations are manual."

---

## 5. Pre-Commit Sequence — Run Every Time

Execute in this exact order. Do not skip steps.

```bash
# Step 1: Design system violations (frontend only)
grep -rn "border-" frontend/src/ \
  | grep -Ev "rounded|outline|border-none|border-0|//|\.md|node_modules"
# Expected: 0 results (if >0 see SKILL_design_system.md Rule 1)

# Step 2: No hardcoded hex in source files
grep -rn "#[0-9A-Fa-f]\{3,6\}" frontend/src/ \
  | grep -Ev "design-system\.css|tailwind\.config|\.md|score-|heat-"
# Expected: 0 results

# Step 3: Old font references gone
grep -rn "Cormorant\|Plus Jakarta\|cormorant\|jakarta" frontend/src/
# Expected: 0 results

# Step 4: Vite build (catches broken imports, JSX errors, missing deps)
cd frontend && npm run build
# Expected: exit code 0, no warnings about missing modules

# Step 5: ESLint
cd frontend && npm run lint
# Expected: exit code 0, "max-warnings 0" is enforced

# Step 6: Confirm you're on a feature branch, not main
git branch --show-current
# Expected: feat/... or fix/... — NEVER "main"
```

Only after all 6 pass: proceed to commit.

---

## 6. Commit Message Format

This project uses **Conventional Commits**. CI does not enforce this via a hook,
but PRs are squash-merged and the message becomes the changelog entry.

Format:
```
<type>(<scope>): <short description>

<body — what changed and why>

<footer — breaking changes or issue refs>
```

Types:
- `feat` — new feature or page
- `fix` — bug fix
- `style` — CSS/design changes that don't affect logic
- `refactor` — code restructuring, no behaviour change
- `chore` — config, deps, tooling

Scopes for frontend work: `ui`, `design`, `landing`, `dashboard`, `auth`, `sidebar`

**Good examples:**
```
feat(ui): implement Digital Atelier token set and typography scale

- Replace Cormorant Garamond/Plus Jakarta Sans with Newsreader/Manrope
- Add full CSS custom property set to design-system.css
- Update tailwind.config.js with new color and font tokens
- Enforce No-Line Rule: removed all 1px solid borders across 8 components
```

```
feat(landing): add public landing page at route /

- New LandingPage.jsx with hero, signal grid, practice area chips
- Glass navbar with Newsreader ORACLE wordmark
- Public route added to App.jsx (no PrivateRoute wrapper)
- 34 practice area chips sourced from CLAUDE.md constants
```

**Bad examples (don't do these):**
```
update UI          ← too vague
fixed stuff        ← useless
WIP                ← never commit WIP to a branch you'll PR
```

---

## 7. Push Sequence

```bash
# 1. Stage only frontend changes
git add frontend/
git add frontend/index.html  # if you modified the font imports

# 2. Verify staged files look right
git diff --staged --stat

# 3. Commit
git commit -m "feat(ui): apply Digital Atelier design system

[your full message body here]"

# 4. Push the feature branch
git push origin feat/digital-atelier-design-system

# 5. Check CI
# Go to: https://github.com/<org>/oracle-bd/actions
# Wait for the CI run on your branch to go green
# If it fails on backend/ checks unrelated to your work, document it
```

---

## 8. When the Push Is Rejected

### Scenario A: Branch protection / required reviews
```bash
# CI passes but GitHub requires a PR review
# Do NOT force push. Do NOT bypass protection.
# Output the branch URL for a human to open the PR:
echo "PR ready: https://github.com/<org>/oracle-bd/compare/feat/your-branch"
```

### Scenario B: Conflicts with main
```bash
git fetch origin
git rebase origin/main
# Resolve conflicts in frontend/ files
# Re-run the full pre-commit sequence (Section 5) after rebase
git push --force-with-lease origin feat/your-branch
# --force-with-lease is safe; --force alone is not
```

### Scenario C: `npm run build` fails in CI but passes locally
This usually means a missing import or a Vite version difference. Check:
```bash
# Ensure you're using the pinned Node version
node --version  # Should be 20.x
# Clear Vite cache
cd frontend && rm -rf node_modules/.vite
npm run build
```

### Scenario D: Vercel build fails after merge to main
Vercel builds the `frontend/` directory. Common causes:
- Environment variable `VITE_API_URL` not set in Vercel project settings
- Import referencing a file that doesn't exist in the repo
- `package.json` dependency added locally but not committed

Check: Is the failing import in a file you created? Is the dependency in `package.json`?

---

## 9. What You Must Never Do

| Action | Why |
|---|---|
| `git push origin main` directly | Triggers production deploy immediately |
| `git push --force origin main` | Can corrupt history, breaks CD |
| Modify `backend/` files | Out of scope; will cause mypy/ruff failures unrelated to your work |
| `npm install <new-package>` without checking `package.json` first | Untested deps can break the Vercel build |
| Add `alembic upgrade head` to any script | DB migrations are manual-only per project rules |
| Commit `.env` or any file with secrets | GitHub will flag it; secrets belong in GitHub Actions secrets |
| Push directly to `main` even if you "just" changed a comment | The CD pipeline will deploy. Every. Time. |

---

## 10. Secrets Reference (Don't Hardcode These)

These exist as GitHub Actions secrets. Never put them in code or `.env` committed
to the repo. Reference `.env.example` for the variable names.

| Secret | Used by |
|---|---|
| `DIGITALOCEAN_ACCESS_TOKEN` | CD — doctl auth |
| `DO_APP_ID` | CD — app update |
| `DO_API_URL` | CD — smoke tests |
| `SMOKE_TEST_TOKEN` | CD — JWT from `POST /api/auth/login` with `admin` / `admin` (or your prod admin); paste `access_token` |
| `SLACK_WEBHOOK_URL` | CD — failure alerts |
| `ANTHROPIC_API_KEY` | Runtime — backend only |

If a smoke test fails in CD, the Slack alert contains the GitHub Actions run URL.
Check it before re-pushing.
