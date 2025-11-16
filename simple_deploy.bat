cd /d C:\Users\naoot\Desktop\syuugyoukisoku
git add -A
git commit -m "Fix Firebase and version issues"
git push origin main
echo Deploy started! Check Cloud Build console.
echo After 2-3 minutes, run switch_traffic.bat
pause
