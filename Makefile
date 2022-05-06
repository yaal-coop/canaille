build:
	python3 setup.py compile_catalog
	python3 setup.py sdist bdist_wheel

init_i18n:
	python3 setup.py extract_messages
	python3 setup.py init_catalog --locale fr
	python3 setup.py compile_catalog
