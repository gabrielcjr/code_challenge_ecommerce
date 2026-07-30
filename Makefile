runserver:
	python manage.py runserver 0.0.0.0:8000

.PHONY: seeds
seeds:
	@echo "Deseja rodar o comando seed? Ao executá-lo, o banco de dados será limpo e as tabelas e fixtures recriadas (s/N)."; \
	read -p "Resposta: " answer; \
	if [ "$$answer" = "s" ]; then \
		python manage.py seed --refresh; \
	else \
		echo "Cancelado"; \
	fi

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

startapp:
	python manage.py startapp $(name)

add-pkg:
	@read -p "Enter package name: " pkg; \
	pip install $$pkg && pip freeze > requirements.txt

pip-install:
	pip install -r requirements.txt

run-check-flake8:
	flake8 . --config .flake8 --count --show-source --statistics

run-check-black:
	black --check . --config pyproject.toml

run-fix-black:
	black . --config pyproject.toml

run-check-isort:
	isort . --check-only --settings-file pyproject.toml

run-fix-isort:
	isort . --settings-file pyproject.toml

run-fix-autoflake:
	autoflake --remove-all-unused-imports --recursive --in-place . --exclude=apps.py,.venv

run-check-linters:
	make run-check-flake8
	make run-check-black
	make run-check-isort

run-fix-linters:
	make run-fix-black
	make run-fix-isort
	make run-fix-autoflake

test:
	USE_SQLITE_FOR_TESTS=1 python manage.py test --verbosity=2

test-coverage:
	USE_SQLITE_FOR_TESTS=1 coverage run --source='.' manage.py test && coverage report

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-migrate:
	docker compose exec web python manage.py migrate

docker-seed:
	docker compose exec web python manage.py seed --refresh

tailwind-init:
	npm install

tailwind-build:
	npx @tailwindcss/cli -i ./static/css/src/input.css -o ./static/css/dist/output.css --minify

tailwind-watch:
	npx @tailwindcss/cli -i ./static/css/src/input.css -o ./static/css/dist/output.css --watch

collectstatic:
	python manage.py collectstatic --noinput

createsuperuser:
	python manage.py createsuperuser

shell:
	python manage.py shell

dbshell:
	python manage.py dbshell