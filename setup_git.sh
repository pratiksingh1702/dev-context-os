#!/usr/bin/env bash
# Standalone Git Initialization Script for AI Developer Context OS

echo "=== Initializing Standalone Git Repository for Context OS ==="

if [ -d ".git" ]; then
    echo "[!] Git repository already initialized."
else
    git init
    echo "[+] Initialized empty Git repository."
fi

git add .
git commit -m "feat: initial commit of AI Developer Context OS (Razorpay Buildathon Open Track)"

REMOTE_URL=
if [ -n "" ]; then
    git remote remove origin 2>/dev/null || true
    git remote add origin ""
    git branch -M main
    echo "[+] Remote origin set to . Run: git push -u origin main"
else
    echo ""
    echo "[*] To push to GitHub, create a new public repo and run:"
    echo "    git remote add origin https://github.com/<your-username>/<your-repo-name>.git"
    echo "    git branch -M main"
    echo "    git push -u origin main"
fi
