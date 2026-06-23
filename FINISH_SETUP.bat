@echo off
title Solar Path - Production setup
color 0A
echo.
echo  Checking live site and printing event URLs...
echo.
python scripts\print_production_urls.py
echo.
python -c "import urllib.request,json,time; u='https://solar-path.onrender.com/health';
import sys
for i in range(12):
 try:
  r=urllib.request.urlopen(u,timeout=25); d=json.loads(r.read());
  print('Health:',d.get('status'),'| beta_gate:',d.get('beta_gate'),'| db:',d.get('database',{}).get('url'));
  sys.exit(0)
 except Exception as e:
  print('Waiting for deploy...',i+1); time.sleep(15)
print('Site not ready yet — check Render dashboard'); sys.exit(1)"
echo.
pause
