.venv: Pipfile
	PIPENV_VENV_IN_PROJECT=true pipenv install --dev
	touch .venv


.PHONY: deps
deps: .venv


.PHONY: test
test: deps
	pipenv run python3 -m tests


.PHONY: lint
lint: deps
	pipenv run flake8 sshc
