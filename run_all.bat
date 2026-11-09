@echo off
REM Run from project root on Windows with Python installed.
python -m pip install -r requirements.txt
python python\run_project.py
python python\forward_plan.py
python python\stress_test.py
python python\build_dashboard.py
pause
