# Standalone Git Initialization Script for AI Developer Context OS
param(
    [string] = ""
)

Write-Host "=== Initializing Standalone Git Repository for Context OS ===" -ForegroundColor Cyan

if (Test-Path ".git") {
    Write-Host "[!] Git repository already initialized." -ForegroundColor Yellow
} else {
    git init
    Write-Host "[+] Initialized empty Git repository." -ForegroundColor Green
}

git add .
git commit -m "feat: initial commit of AI Developer Context OS (Razorpay Buildathon Open Track)"

if ( -ne "") {
    git remote remove origin 2>
    git remote add origin 
    git branch -M main
    Write-Host "[+] Remote origin set to . Run: git push -u origin main" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[*] To push to GitHub, create a new public repo and run:" -ForegroundColor Yellow
    Write-Host "    git remote add origin https://github.com/<your-username>/<your-repo-name>.git" -ForegroundColor White
    Write-Host "    git branch -M main" -ForegroundColor White
    Write-Host "    git push -u origin main" -ForegroundColor White
}
