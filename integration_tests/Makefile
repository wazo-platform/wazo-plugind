.PHONY: test-setup build-plugind test create-git

create-git:
	./make-git-repo.sh

test-setup: build-plugind create-git pull-images ;

egg-info:
	cd .. && python setup.py egg_info

pull-images:
	docker pull wazopbx/xivo-auth-mock
	docker pull python:3.5.3
	docker pull n3llyb0y/wait
	docker pull rabbitmq
	docker pull consul
	docker pull swaggerapi/swagger-validator

build-plugind:
	docker build -t wazopbx/wazo-plugind ..
	docker build --no-cache -t wazo-plugind-test -f Dockerfile ..

test:
	nosetests -x
