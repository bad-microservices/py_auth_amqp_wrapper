checkfiles = py_auth_amqp_wrapper/

help:
	@echo "py_auth_amqp_wrapper Makefile"
	@echo "usage: make <target>"
	@echo "Targets:"
	@echo "    - package   Build py_auth_amqp_wrapper as package"
	@echo "    - deps      Installs needed Dependencies"
	@echo "    - devdeps   Installs needed Dependencies for development"

deps:
	pipenv install

devdeps:
	pipenv install --dev


package: devdeps
	rm -fR dist/
	pipenv run python -m build -n
