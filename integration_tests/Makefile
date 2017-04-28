.PHONY: test-setup build-plugind test create-git

create-git:
	./make-git-repo.sh

test-setup: build-plugind create-git
	docker pull wazopbx/xivo-auth-mock
	docker pull python:3.4.2
	docker pull n3llyb0y/wait
	docker pull rabbitmq
	docker pull consul
	docker pull swaggerapi/swagger-validator

build-plugind:
	docker build -t wazopbx/wazo-plugind ..

test:
	nosetests -x
