# One-click GitHub push script for Windows PowerShell
# Commits & pushes strictly as IamSamk <kadam.samartha@yahoo.com> with NO AI co-author
$ErrorActionPreference = "Stop"

if (-not (Test-Path ".git")) {
    git init -b main
}
git config user.name "IamSamk"
git config user.email "kadam.samartha@yahoo.com"
git branch -M main

$remotes = git remote
if ($remotes -notcontains "origin") {
    git remote add origin https://github.com/IamSamk/Linkedinconnector.git
} else {
    git remote set-url origin https://github.com/IamSamk/Linkedinconnector.git
}

git add -A
$status = git status --porcelain
if ($status) {
    $env:GIT_AUTHOR_NAME = "IamSamk"
    $env:GIT_AUTHOR_EMAIL = "kadam.samartha@yahoo.com"
    $env:GIT_COMMITTER_NAME = "IamSamk"
    $env:GIT_COMMITTER_EMAIL = "kadam.samartha@yahoo.com"
    git commit -m "feat: initialize LinkedIn Public OSINT & Cohort Discovery Suite (Next.js 16.4.2 + FastAPI 0.162.0)"
}

Write-Host "Pushing main -> https://github.com/IamSamk/Linkedinconnector.git as IamSamk <kadam.samartha@yahoo.com>..."
git push -u origin main
