IMAGE_NAME = leads_app
CONTAINER_NAME = leads_app_container
PORT = 80
ENV_FILE = .env

build:
	docker build -t $(IMAGE_NAME) .

run:
	docker run -d -p $(PORT):8000 --env-file $(ENV_FILE) --name $(CONTAINER_NAME) $(IMAGE_NAME)

stop:
	docker stop $(CONTAINER_NAME)
	docker rm $(CONTAINER_NAME)

restart: stop build run

logs:
	docker logs -f $(CONTAINER_NAME)

clean:
	docker rmi $(IMAGE_NAME)

cov:
	pytest --cov
	rm .coverage