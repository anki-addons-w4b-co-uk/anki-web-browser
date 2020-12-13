clear
echo updating -- anki-web-browser ankiaddon
7z u anki_web_browser.ankiaddon ../src/* -xr0!__pycache__ -xr!__pycache__
echo done
start anki_web_browser.ankiaddon
exec $SHELL
