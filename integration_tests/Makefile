create-git:
	./make-git-repo.sh

test-setup: egg-info build-plugind create-git

egg-info:
	cd .. && python setup.py egg_info

build-plugind:
	docker build -t wazoplatform/wazo-plugind ..
	docker build --no-cache -t wazo-plugind-test -f Dockerfile ..

test:
	pytest -x

.PHONY: test-setup build-plugind test create-git
