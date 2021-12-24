node_modules: package.json
	npm i --dev


deps: node_modules


.PHONY: test
test: deps
	npm run test


.PHONY: lint
lint:
	npm run lint


.PHONY: ci
ci: test lint
