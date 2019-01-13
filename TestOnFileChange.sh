find . -name "*.py" | entr python -m unittest discover --pattern "*test.py" -s .
