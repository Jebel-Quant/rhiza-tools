# Testing Guide: Bump and Release Commands

This guide provides step-by-step testing procedures for all user interaction flows with the enhanced `bump` and `release` commands.

## Prerequisites

Before testing, ensure you have:
- A clean git repository with at least one commit
- Configured git remote (origin)
- Python environment set up with rhiza-tools installed

## 🧪 Bump Command Testing

### Test 1: Interactive Bump (Default Behavior)

**Command:**
```bash
rhiza-tools bump
```

**Expected Flow:**
1. Prompt: "Select bump type (Current: X.Y.Z)"
   - Options shown: Patch, Minor, Major, Alpha, Beta, RC, Dev, Prerelease, Build
2. After selection, shows preview:
   ```
   Preview of changes:
     Version: X.Y.Z → X.Y.(Z+1)
     Branch: <current-branch>
   ```
3. Prompt: "Proceed with version bump? (Y/n)"
4. If yes, version is bumped
5. Success message: "Version bumped: X.Y.Z -> X.Y.(Z+1)"

**Test Steps:**
```bash
# Step 1: Start interactive bump
rhiza-tools bump

# Step 2: Select "Patch" from the menu
# Step 3: Confirm the preview by pressing Y
# Step 4: Verify version changed in pyproject.toml
cat pyproject.toml | grep version

# Step 5: Check git status
git status
# Should show modified: pyproject.toml (if not committed)
```

**Rollback:**
```bash
git checkout pyproject.toml
```

---

### Test 2: Interactive Bump with Push

**Command:**
```bash
rhiza-tools bump --push
```

**Expected Flow:**
1. Same as Test 1, steps 1-5
2. Additional prompt: "Push changes to remote? (y/N)"
3. If yes, changes are pushed to remote

**Test Steps:**
```bash
# Step 1: Ensure you're on a branch that can be pushed
git checkout -b test-bump-push

# Step 2: Run interactive bump with push
rhiza-tools bump --push

# Step 3: Select bump type (e.g., "Patch")
# Step 4: Confirm preview
# Step 5: Decline push when prompted (press N)
# Step 6: Verify changes are committed but not pushed
git log -1
git status

# Step 7: Clean up
git reset --hard HEAD~1
git checkout main
git branch -D test-bump-push
```

---

### Test 3: Non-Interactive Bump with Dry-Run

**Command:**
```bash
rhiza-tools bump minor --dry-run
```

**Expected Output:**
```
Current branch: <branch-name>
Current version: X.Y.Z
New version will be: X.(Y+1).0
[Running bump-my-version in dry-run mode - shows what would change]
```

**Test Steps:**
```bash
# Step 1: Note current version
cat pyproject.toml | grep version

# Step 2: Run dry-run
rhiza-tools bump minor --dry-run

# Step 3: Verify no changes were made
git status
# Should show "nothing to commit, working tree clean"

# Step 4: Verify version unchanged
cat pyproject.toml | grep version
```

---

### Test 4: Non-Interactive Bump with Commit and Push

**Command:**
```bash
rhiza-tools bump patch --commit --push
```

**Expected Flow:**
1. Version is bumped automatically
2. Changes are committed automatically
3. Changes are pushed to remote automatically
4. No prompts shown

**Test Steps:**
```bash
# Step 1: Create test branch
git checkout -b test-auto-bump
git push -u origin test-auto-bump

# Step 2: Run non-interactive bump with push
rhiza-tools bump patch --commit --push

# Step 3: Verify commit was created
git log -1 --oneline

# Step 4: Verify changes were pushed
git log origin/test-auto-bump -1

# Step 5: Clean up
git checkout main
git push origin --delete test-auto-bump
git branch -D test-auto-bump
```

---

### Test 5: Bump on Specific Branch

**Command:**
```bash
rhiza-tools bump minor --branch feature-branch
```

**Expected Flow:**
1. Switches to feature-branch
2. Bumps version
3. Returns to original branch

**Test Steps:**
```bash
# Step 1: Create a feature branch
git checkout -b feature-branch
git checkout main

# Step 2: Run bump on feature branch
rhiza-tools bump minor --branch feature-branch --dry-run

# Step 3: Verify still on main branch
git branch --show-current
# Should show "main"

# Step 4: Check feature branch has changes (without --dry-run)
rhiza-tools bump patch --branch feature-branch --commit
git checkout feature-branch
cat pyproject.toml | grep version

# Step 5: Clean up
git checkout main
git branch -D feature-branch
```

---

### Test 6: Bump with Dry-Run and Preview

**Command:**
```bash
rhiza-tools bump major --dry-run
```

**Expected Output:**
- Shows current and new version
- Shows what files would be modified
- No actual changes made

**Test Steps:**
```bash
# Step 1: Run dry-run
rhiza-tools bump major --dry-run

# Step 2: Verify no changes
git status
git diff pyproject.toml
```

---

## 🚀 Release Command Testing

### Test 7: Interactive Release (Default Behavior)

**Command:**
```bash
rhiza-tools release
```

**Expected Flow:**
1. Shows current branch
2. Prompt: "Would you like to bump the version before releasing? (y/N)"
3. If yes, prompts for bump type (PATCH/MINOR/MAJOR)
4. Performs bump
5. Shows current version and expected tag
6. Shows commits since last tag
7. Prompt: "Push tag to remote and trigger release workflow? (y/N)"
8. If yes, pushes tag

**Test Steps:**
```bash
# Prerequisites: Ensure you have a tagged version
git tag v0.1.0  # If no tags exist

# Step 1: Start interactive release
rhiza-tools release

# Step 2: Decline version bump (press N)
# Step 3: Verify tag information is shown
# Step 4: Decline push (press N)
# Step 5: Verify tag was not pushed
git ls-remote --tags origin | grep v0.2.3
```

---

### Test 8: Interactive Release with Bump

**Command:**
```bash
rhiza-tools release
```

**Expected Flow:**
1. Same as Test 7
2. Accept bump prompt (Y)
3. Select bump type (e.g., MINOR)
4. Version is bumped
5. Tag is created
6. Prompted to push

**Test Steps:**
```bash
# Step 1: Start interactive release
rhiza-tools release

# Step 2: Accept bump (press Y)
# Step 3: Select MINOR
# Step 4: Decline push (press N)
# Step 5: Verify version was bumped
cat pyproject.toml | grep version

# Step 6: Verify tag exists locally
git tag -l | grep v0.3.0

# Step 7: Rollback
git reset --hard HEAD~1
git tag -d v0.3.0
```

---

### Test 9: Non-Interactive Release with Dry-Run

**Command:**
```bash
rhiza-tools release --dry-run
```

**Expected Output:**
```
Current branch: <branch-name>
Current version: X.Y.Z
Expected tag: vX.Y.Z
[Shows what would happen without doing it]
[DRY-RUN] Release tag vX.Y.Z would be pushed to remote
[DRY-RUN] Release process completed (no changes made)
```

**Test Steps:**
```bash
# Step 1: Run dry-run
rhiza-tools release --dry-run

# Step 2: Verify no changes
git status
git tag -l  # Tag list should be unchanged
```

---

### Test 10: Non-Interactive Release with Bump and Push

**Command:**
```bash
rhiza-tools release --bump MINOR --push --dry-run
```

**Expected Flow:**
1. Bumps version to next minor
2. Creates tag
3. Shows what would be pushed
4. No actual push in dry-run

**Test Steps:**
```bash
# Step 1: Run with dry-run first
rhiza-tools release --bump MINOR --push --dry-run

# Step 2: Verify output shows:
#   - Version bump preview
#   - Tag creation
#   - Push simulation

# Step 3: Run without dry-run on test branch
git checkout -b test-release
rhiza-tools release --bump PATCH --push

# Step 4: Verify tag was pushed
git ls-remote --tags origin

# Step 5: Clean up
git checkout main
git push origin --delete test-release
git branch -D test-release
```

---

### Test 11: Release Without Bump (Just Push Tag)

**Command:**
```bash
rhiza-tools release --push
```

**Expected Flow:**
1. Uses current version
2. Validates repository state
3. Pushes existing tag to remote
4. No version bump

**Test Steps:**
```bash
# Prerequisites: Ensure current version has a tag
git tag v0.2.3  # Create tag if doesn't exist

# Step 1: Run release without bump
rhiza-tools release --push --dry-run

# Step 2: Verify it would push existing tag
# Output should show: "Release tag v0.2.3 would be pushed"

# Step 3: Actual push (on test branch)
git checkout -b test-release-only
git push -u origin test-release-only
rhiza-tools release --push

# Step 4: Clean up
git checkout main
git push origin --delete test-release-only
git branch -D test-release-only
```

---

### Test 12: Release with Commit Listing

**Command:**
```bash
rhiza-tools release
```

**Expected Output:**
Shows list of commits since last tag:
```
Commits included in this release (since v0.2.2):
  • abc1234 Add new feature
  • def5678 Fix bug in parser
  • ghi9012 Update documentation
```

**Test Steps:**
```bash
# Prerequisites: Make some commits since last tag
echo "test" > test.txt
git add test.txt
git commit -m "Test commit 1"
echo "test2" >> test.txt
git commit -am "Test commit 2"

# Step 1: Run release
rhiza-tools release --dry-run

# Step 2: Verify commit list is shown
# Should display the 2 test commits

# Step 3: Clean up
git reset --hard HEAD~2
rm -f test.txt
```

---

## ✅ Verification Checklist

After each test, verify:

- [ ] Command completes without errors
- [ ] Prompts appear as expected (interactive mode)
- [ ] No prompts appear (non-interactive mode)
- [ ] Version changes are correct
- [ ] Git operations succeed/fail as expected
- [ ] Dry-run doesn't make actual changes
- [ ] Branch information is displayed
- [ ] Rollback/recovery works properly

## 🔄 Common Rollback Commands

```bash
# Undo uncommitted version change
git checkout pyproject.toml

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1

# Delete local tag
git tag -d vX.Y.Z

# Delete remote tag
git push origin --delete vX.Y.Z

# Return to original branch
git checkout main
```

## 🐛 Error Scenarios to Test

### Test 13: Bump with Dirty Working Directory

**Command:**
```bash
# Make uncommitted changes
echo "test" > test.txt
git add test.txt

# Try to bump
rhiza-tools bump patch
```

**Expected:** Should fail unless `--allow-dirty` is used

---

### Test 14: Release with Missing Tag

**Command:**
```bash
# Ensure no tag exists for current version
git tag -d v0.2.3  # If exists

# Try to release
rhiza-tools release
```

**Expected:** Error message: "Tag 'vX.Y.Z' does not exist locally"

---

### Test 15: Release with Existing Remote Tag

**Command:**
```bash
# Push a tag
git tag v0.2.3
git push origin v0.2.3

# Try to release again
rhiza-tools release
```

**Expected:** Error message: "Tag 'vX.Y.Z' already exists on remote"

---

### Test 16: Branch Switching Failure

**Command:**
```bash
# Create uncommitted changes
echo "test" > test.txt

# Try to bump on different branch
rhiza-tools bump patch --branch other-branch
```

**Expected:** Should fail or prompt to commit changes first

---

## 📝 Test Results Template

Use this template to record test results:

```
Test #: ___
Command: _______________
Status: [ ] Pass [ ] Fail
Notes: _______________
Issues Found: _______________
```

## 🎯 Summary

This testing guide covers:
- ✅ 6 bump command scenarios
- ✅ 6 release command scenarios  
- ✅ 4 error scenarios
- ✅ All interactive and non-interactive modes
- ✅ All dry-run capabilities
- ✅ All rollback procedures

All tests include dry-run options where applicable to preview changes safely before execution.
