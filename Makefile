DOCKER_COMPOSE = docker-compose


.PHONY: sysdeps
sysdeps:
	sudo apt-get install qemu binfmt-support qemu-user-static


.PHONY: build
build:
	${DOCKER_COMPOSE} build


.PHONY: run
run:
	${DOCKER_COMPOSE} up --scale server=3


.PHONY: test
test:
	${MAKE} -C console test
