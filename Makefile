PY ?= python3

.PHONY: validate build estimate placeholders preview final
validate:
	$(PY) -m pipeline validate
build:
	$(PY) -m pipeline build
estimate:
	$(PY) -m pipeline estimate
placeholders:
	$(PY) -m pipeline placeholders
preview:
	$(PY) -m pipeline assemble --allow-placeholders --preview
final:
	$(PY) -m pipeline assemble
