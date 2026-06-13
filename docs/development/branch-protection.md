# Branch protection (as code)

The protection rules for the default branch (`main`) are codified in
[`.github/rulesets/main-branch-protection.json`](https://github.com/Jebel-Quant/rhiza-tools/blob/main/.github/rulesets/main-branch-protection.json)
as a GitHub **repository ruleset**, so they are reviewable and version-controlled
rather than living only in the repository settings UI.

## What the ruleset enforces

On `main`:

- **Pull request required** — no direct pushes; changes land through a PR with
  **at least one approving review**, and stale approvals are dismissed when new
  commits are pushed.
- **Required status checks** (branch must be up to date before merge):
  the full CI gate — pre-commit, security scanning, validation, deptry,
  license-compliance, docs-coverage, lowest-direct-dependency compatibility,
  `ty` type checking on 3.11–3.14, the `test` matrix across
  {3.11, 3.12, 3.13, 3.14} × {ubuntu, macOS, windows}, and the CodeQL
  `python` / `actions` analyses.
- **Linear history** — merge commits that would create non-linear history are
  rejected (squash/rebase/merge are all permitted as merge methods).
- **No force pushes** and **no branch deletion**.

Heavy or external checks that do not run deterministically on every PR
(ClusterFuzzLite, CodeFactor, the Marimo notebook matrix) are intentionally
**not** required, so they never block an otherwise-green PR.

## Applying / updating the ruleset

The JSON is in the REST API shape, so it can be applied directly. Create it once:

```bash
gh api --method POST repos/Jebel-Quant/rhiza-tools/rulesets \
  --input .github/rulesets/main-branch-protection.json
```

To update an existing ruleset, find its id and `PUT` the same file:

```bash
RULESET_ID=$(gh api repos/Jebel-Quant/rhiza-tools/rulesets \
  --jq '.[] | select(.name=="main-branch-protection") | .id')
gh api --method PUT repos/Jebel-Quant/rhiza-tools/rulesets/"$RULESET_ID" \
  --input .github/rulesets/main-branch-protection.json
```

The committed JSON is the source of truth: change it in a PR, then re-`PUT` it.

## Notes for a solo maintainer

The required approving review means GitHub will not let a non-admin merge a PR
without a second account approving it (you cannot approve your own PR). To keep
the gate in place for everyone else while letting the maintainer move when
needed, the ruleset grants the **repository admin** role a bypass:

```json
"bypass_actors": [
  { "actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always" }
]
```

With `bypass_mode: always`, a repository admin can merge their own PRs (and push
directly) without the rules blocking them; the rules still apply to everyone
else. Managing the ruleset itself is never blocked by the ruleset.
