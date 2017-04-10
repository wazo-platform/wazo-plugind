.PHONY: test-setup build-plugind test

test-setup: build-plugind
	docker pull python:3.4.2
	docker pull n3llyb0y/wait
	docker pull consul

build-plugind:
	docker build -t wazopbx/wazo-plugind ..

test:
	nosetests -x
