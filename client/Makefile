.PHONY: sysdeps
sysdeps:
	pip install pipenv


.venv: Pipfile sysdeps
	PIPENV_VENV_IN_PROJECT=true pipenv install --dev


.PHONY: deps
deps: .venv


.PHONY: test
test: deps
	pipenv run python3 -m tests


.PHONY: lint
lint: deps
	pipenv run flake8 conduit_client
