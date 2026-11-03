#!/usr/bin/env bash
# One-click GitHub push script for Bash / Linux / macOS / Git Bash
# Commits & pushes strictly as IamSamk <kadam.samartha@yahoo.com> with NO AI co-author
set -e

if [ ! -d ".git" ]; then
    git init -b main
fi
git config user.name "IamSamk"
git config user.email "kadam.samartha@yahoo.com"
git branch -M main

git remote set-url origin https://github.com/IamSamk/Linkedinconnector.git 2>/dev/null || git remote add origin https://github.com/IamSamk/Linkedinconnector.git

git add -A
if [ -n "$(git status --porcelain)" ]; then
    GIT_AUTHOR_NAME="IamSamk"     GIT_AUTHOR_EMAIL="kadam.samartha@yahoo.com"     GIT_COMMITTER_NAME="IamSamk"     GIT_COMMITTER_EMAIL="kadam.samartha@yahoo.com"     git commit -m "feat: initialize LinkedIn Public OSINT & Cohort Discovery Suite (Next.js 16.4.2 + FastAPI 0.162.0)"
fi

echo "Pushing main -> https://github.com/IamSamk/Linkedinconnector.git as IamSamk <kadam.samartha@yahoo.com>..."
git push -u origin main
