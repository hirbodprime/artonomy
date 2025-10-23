echo "test deploy $(date)" >> README.md
git add README.md
git commit -m "Test CI/CD deploy"
git push origin main
