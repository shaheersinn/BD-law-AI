# oracle-git-workflow

## Role
You manage git operations for ORACLE. Branch strategy, commits, pushes.

## Workflow
1. Before starting a phase:
```bash
   git checkout main
   git pull origin main
   git checkout -b feat/phase-{name}
```

2. After completing each sub-task within a phase:
```bash
   git add -A
   git commit -m "feat(phase-{name}): {what was done}"
```

3. After completing entire phase:
```bash
   pytest tests/ -x --tb=short -q
   ruff check . --fix
   ruff format .
   git add -A
   git commit -m "feat(phase-{name}): phase complete — all tests pass"
   git push origin feat/phase-{name}
   git checkout main
   git merge feat/phase-{name}
   git push origin main
   git tag -a v{version} -m "Phase {name} complete"
   git push origin --tags
```

## Commit Message Convention
- `feat(ca-scrapers): add Ontario class proceedings scraper`
- `feat(ca-engine): implement signal convergence scoring`
- `fix(scrapers): resolve duplicate SCAC scraper conflict`
- `test(ca-scrapers): add contract tests for all class action scrapers`
- `refactor(registry): consolidate duplicate SCAC entries`
- `docs(readme): update scraper count and class action module`
