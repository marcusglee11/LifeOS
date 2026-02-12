@echo off
setlocal
wsl.exe -d Ubuntu -e bash -lic "cd /mnt/c/Users/cabra/Projects/LifeOS && coo stop"
endlocal

