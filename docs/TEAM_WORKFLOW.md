# HepatiQ Team Workflow

This is a **student team project** at Sharda University's Anand School of Engineering & Technology. We follow a simple, professional workflow designed for academic collaboration — clear enough to prevent confusion, lightweight enough to stay agile.

## Core Principle

- **`main` is always stable.** Never commit directly to main unless it's a critical hotfix.
- **Feature branches isolate work.** Each team member works on their own branch.
- **Pull requests are mandatory** for code review and project coherence.
- **Keep changes focused.** One PR = one task. Easier to review, easier to debug if something breaks.

## Branch Naming Convention

Use a simple, readable format: `firstname-task-description`

**Good examples:**

```bash
nirali-dataset-cleanup
pranjal-fastapi-endpoint
deekshitha-streamlit-dashboard
rudra-bootstrap-ci
```

**Avoid:**
- `test`, `dev`, `fix` (too vague)
- `NIR-123` (commit messages are for that)
- Spaces, special characters (use hyphens)

## Workflow Steps

### 1. Start from `main`
```bash
git checkout main
git pull origin main
```

### 2. Create your feature branch
```bash
git checkout -b your-name-your-task
```

### 3. Make your changes
- Work in your assigned folder (see [GETTING_STARTED.md](GETTING_STARTED.md))
- Write clean, readable code
- Test locally before committing
- Keep commits logical and focused

### 4. Write clear commit messages
```bash
git add .
git commit -m "Add SHAP waterfall visualization to backend"
```

**Good commit message format:**
- Use present tense ("Add" not "Added")
- Be specific ("Add SHAP waterfall chart" not "Fix bug")
- Reference the feature or fix, not the syntax

### 5. Push and open a Pull Request
```bash
git push origin your-name-your-task
```

Then:
1. Go to GitHub → your branch
2. Click **Compare & pull request**
3. Write a clear title and description:
   - What did you change?
   - Why did you change it?
   - What was tested?
   - Any known limitations or follow-up work?

### 6. Code review
- Tag a teammate for review
- Be responsive to feedback — most PRs get feedback
- Don't take it personally; we're all learning
- Make requested changes locally, then push again

### 7. Merge and clean up
- Once approved, **squash-merge** small PRs (one feature = one commit on main)
- Use regular merge if the commit history is useful/instructive
- Delete the feature branch after merge

```bash
git checkout main
git pull origin main
git branch -d your-name-your-task
```

## Pull Request Guidelines

**Every PR should include:**

| Field | Example |
|-------|---------|
| **Title** | "Add SHAP waterfall chart to backend" |
| **Description** | What changed, why, what was tested |
| **Related Issue** | Closes #42 (if applicable) |
| **Testing** | "Tested locally with toy model and live API" |
| **Scope** | One focused feature or bugfix per PR |

**Poor PR example:**
```
Title: "Updates"
Description: (empty)
```

**Good PR example:**
```
Title: "Add SHAP waterfall visualization to backend"

Description:
- Integrates SHAP Explainer in /predict endpoint
- Returns per-feature attribution for each prediction
- Tested with toy model and 5 sample patients
- Related to issue #12: Feature Importance Visualization
```

## Code Review Expectations

**As a reviewer:**
- Try to review PRs within 24 hours when possible
- Check for correctness, clarity, and fit with the project
- Ask questions if something is unclear
- Suggest improvements, but don't be picky about style
- Approve once satisfied; use GitHub's "Request Changes" if needed

**As the author:**
- Address feedback promptly
- Push changes to the same branch; GitHub auto-updates the PR
- Respond to each comment (even if just "Done" or "Good catch")
- Re-request review after making changes

**What blocks a merge:**
- Broken code or failed tests
- Missing tests for new features
- Major logic errors or security issues
- Unrelated changes bundled into one PR

## Hotfix / Urgent Merge Policy

**Avoid direct pushes to `main`.** But if something is critically broken:

1. Create a hotfix branch (`yourname-urgent-fix`)
2. Make the minimal fix
3. Open a PR with `[URGENT]` in the title
4. Get one quick approval
5. Merge immediately

Example:
```bash
git checkout main
git checkout -b nirali-urgent-dataset-fix
# ... fix the bug
git push origin nirali-urgent-dataset-fix
# Open PR → review → merge
```

This keeps `main` safe while staying agile.

## Merge Strategies

**Squash merge** (recommended for most PRs):
```bash
git merge --squash your-name-your-task
```
- Combines all your commits into one clean commit on main
- Keeps main's history readable
- Best for: feature branches, bugfixes, small updates

**Regular merge** (for substantial work):
- Use when the commit history is instructive or the work was long
- Best for: major milestones, work spanning multiple days with clear progression

**Avoid:** Rebasing on main (can cause confusion in team settings)

## Team Spirit & Communication

This workflow exists to serve the project, not to create friction. Remember:

- **Be responsive** — reply to reviews within 24 hours when possible
- **Ask for help early** — don't wait until you're stuck for days
- **Give constructive feedback** — "I'd suggest doing X because..." beats "Wrong"
- **Respect boundaries** — don't modify someone else's folder without asking
- **Test before pushing** — catch your own bugs early
- **Document as you go** — make it easy for teammates to understand your code

If something feels off (workflow too slow, process too heavy, unclear responsibilities), bring it up in the team chat. We can iterate and improve.

## Workflow at a Glance

```
Start:   git checkout main → git pull origin main
         git checkout -b yourname-task
         
Work:    Edit files → git add . → git commit -m "clear message"
         
Push:    git push origin yourname-task
         Open PR on GitHub → Request review
         
Review:  Address feedback → Push changes to same branch
         
Merge:   Approve → Squash merge to main
         Delete feature branch
         
Done:    git checkout main → git pull
         Start next task
```

---

**Questions?** Check [GETTING_STARTED.md](GETTING_STARTED.md) or tag a teammate on GitHub.
