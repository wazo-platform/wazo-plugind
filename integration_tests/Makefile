.PHONY: test-setup build-dird test

test-setup: build-dird
	docker pull python:3.4.2
	docker pull n3llyb0y/wait

build-dird:
	docker build -t wazopbx/wazo-plugind ..

test:
	nosetests -x
