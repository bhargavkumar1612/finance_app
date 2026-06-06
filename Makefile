.PHONY: dev test-unit test-integration test-smoke test-e2e test-e2e-smoke

dev:
	docker compose up

test-unit:
	docker compose run --rm -w /app/apps/api -e PYTHONPATH=/app/apps/api api pytest tests/unit -q

test-integration:
	./scripts/test-in-docker.sh tests/integration -q

test-smoke:
	./scripts/test-in-docker.sh tests/smoke -q

test-e2e:
	cd e2e && npx playwright install --with-deps && npx playwright test

test-e2e-smoke:
	cd e2e && npx playwright test --grep @smoke
