.PHONY: install test lint run eval docker

install:
	python -m pip install -e '.[dev]'

test:
	python -m pytest -q

lint:
	ruff check .

run:
	uvicorn aegis_forge.api:app --reload

eval:
	aegis --eval

docker:
	docker compose up --build
