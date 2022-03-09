node_modules: package-lock.json
	npm i --dev
	touch node_modules


.PHONY: deps
deps: node_modules


.PHONY: test
test: deps
	npm run test


.PHONY: lint
lint: deps
	npm run lint
