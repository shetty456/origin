.PHONY: up build down restart logs shell migrate makemigrations createsuperuser test

up:
	docker compose up

build:
	docker compose up --build

down:
	docker compose down

restart:
	docker compose down && docker compose up

logs:
	docker compose logs -f web

shell:
	docker compose exec web python manage.py shell

migrate:
	docker compose exec web python manage.py migrate

makemigrations:
	docker compose exec web python manage.py makemigrations $(app)

createsuperuser:
	docker compose exec web python manage.py createsuperuser

test:
	docker compose exec web python manage.py test $(app)

psql:
	docker compose exec db psql -U ${DB_USER:-origin} -d ${DB_NAME:-origin}
