DOCKER_COMPOSE = docker-compose


.PHONY: sysdeps
sysdeps:
	sudo apt-get install qemu binfmt-support qemu-user-static


.venv: Pipfile
	PIPENV_VENV_IN_PROJECT=true pipenv install
	touch .venv


.PHONY: deps
deps: .venv


.PHONY: build
build:
	${DOCKER_COMPOSE} build


.PHONY: run
run:
	${DOCKER_COMPOSE} up --scale server=3


.PHONY: test
test:
	${MAKE} -C proxy test


.PHONY: lint
lint:
	${MAKE} -C proxy lint


.PHONY: ci
ci: test lint


.PHONY: load
load: deps
	xdg-open http://0.0.0.0:8089
	pipenv run locust --host=http://test_host.shanty.local:8080/
