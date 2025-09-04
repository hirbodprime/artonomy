import os
import subprocess

# Absolute path to venv activate.bat
venv_activate = os.path.abspath("../myvenv/Scripts/activate.bat")

# Project folder where manage.py lives
project_dir = os.path.abspath(".")

# Commands after venv activation
commands = f'cd "{project_dir}" && python manage.py runserver'

# Run in cmd with venv activated
subprocess.call(f'cmd.exe /k "{venv_activate} && {commands}"')
