.PHONY: test-setup build-plugind test create-git

create-git:
	./make-git-repo.sh

test-setup: build-plugind create-git pull-images ;

egg-info:
	cd .. && python setup.py egg_info

pull-images:
	docker pull consul
	docker pull python:3.5.3
	docker pull rabbitmq
	docker pull swaggerapi/swagger-validator
	docker pull wazopbx/wait
	docker pull wazopbx/xivo-auth-mock

build-plugind:
	docker build -t wazopbx/wazo-plugind ..
	docker build --no-cache -t wazo-plugind-test -f Dockerfile ..

test:
	nosetests -x
