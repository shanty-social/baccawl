DOCKER_COMPOSE = docker-compose


.PHONY: shared
shared:
	-${DOCKER} network create --subnet=192.168.100.0/24 --ip-range=192.168.100.0/25 --gateway=192.168.100.254 shared


.PHONY: build
build:
	${DOCKER_COMPOSE} build


.PHONY: run
run: shared
	${DOCKER_COMPOSE} up --remove-orphans --scale ssdh=2


.PHONY: test
test:
	${MAKE} -C sshd test
	${MAKE} -C client test


.PHONY: lint
lint:
	${MAKE} -C sshd lint
	${MAKE} -C client lint


.PHONY: ci
ci: test lint


.PHONY: load
load: deps
	xdg-open http://0.0.0.0:8089
	pipenv run locust --host=http://test_host.shanty.local:8080/


.PHONY: clean
clean:
	${DOCKER_COMPOSE} rm --force
