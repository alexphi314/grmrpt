ifeq ($(tag), dev)
	IMAGE_TAG=latest
	EB_ENV=dockerdev2
else
	IMAGE_TAG=master
	EB_ENV=dockerprod
endif

setup:
	pip install awsebcli django-nose
	make test

build:
	python grmrpt_site/manage.py collectstatic --noinput
	docker-compose -f docker-compose.dev.yml run django python3 /src/manage.py makemigrations
	docker-compose -f docker-compose.dev.yml down
	docker-compose -f docker-compose.dev.yml build
	./generate_dockerrun.sh Dockerrun.aws.json.template $(IMAGE_TAG)

test: build
	docker-compose -f docker-compose.test.yml up --exit-code-from django

push: test
	docker image tag grmrpt_django:latest alexphi981/grmrptcore:$(shell git rev-parse HEAD)
	docker push alexphi981/grmrptcore:$(shell git rev-parse HEAD)
	docker tag alexphi981/grmrptcore:$(shell git rev-parse HEAD) alexphi981/grmrptcore:$(IMAGE_TAG)
	docker push alexphi981/grmrptcore:$(IMAGE_TAG)

	docker image tag grmrpt_nginx:latest alexphi981/nginx:$(shell git rev-parse HEAD)
	docker push alexphi981/nginx:$(shell git rev-parse HEAD)
	docker tag alexphi981/nginx:$(shell git rev-parse HEAD) alexphi981/nginx:$(IMAGE_TAG)
	docker push alexphi981/nginx:$(IMAGE_TAG)

shell:
	docker exec -ti $(container) /bin/bash

deploy: push
	eb use $(EB_ENV)
	eb deploy