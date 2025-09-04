@echo off
REM Go to venv
cd ..\myvenv\Scripts
call activate

REM Go back to project folder (adjust if your manage.py is elsewhere)
cd ..\..\artonomy

REM Run the server
python manage.py runserver
