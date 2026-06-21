.PHONY: dev lint test smoke compile clean precommit

dev:
	flask run --debug

lint:
	ruff check app/ tests/
	ruff format --check app/ tests/

test:
	pytest -x -q --tb=short

smoke:
	pytest tests/smoke -x -q --tb=short

compile:
	python -m compileall -q app/ tests/

precommit:
	pre-commit run --all-files

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
