.PHONY: test
test:
	py.test --cov=aiogoogle

.PHONY: test-buildcov
test-buildcov:
	py.test --cov=aiogoogle && (echo "building coverage html, view at './htmlcov/index.html'"; coverage html)
