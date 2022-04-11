venv: venv/touchfile


venv/touchfile: requirements.txt
	test -d venv || python3 -m venv venv
	. venv/bin/activate; pip3 install -Ur requirements.txt
	touch venv/touchfile


autobuild: venv
	. venv/bin/activate; sphinx-autobuild . _build/index.html --port 8001


clean:
	rm -rf venv _build _static _templates docs
