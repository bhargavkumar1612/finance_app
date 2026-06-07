.PHONY: dev test-unit test-integration test-smoke test-web-unit test-e2e test-e2e-smoke test-e2e-desktop test-e2e-mobile

dev:
	docker compose up

test-unit:
	docker compose run --rm -w /app/apps/api -e PYTHONPATH=/app/apps/api api pytest tests/unit -q

test-integration:
	./scripts/test-in-docker.sh tests/integration -q

test-smoke:
	./scripts/test-in-docker.sh tests/smoke -q

test-web-unit:
	cd apps/web && npm test

test-e2e:
	cd e2e && npx playwright install --with-deps && npx playwright test

test-e2e-desktop:
	cd e2e && npx playwright test --project=desktop-chromium

test-e2e-mobile:
	cd e2e && npx playwright test --project=mobile-chrome

test-e2e-smoke:
	cd e2e && npx playwright test --grep @smoke
