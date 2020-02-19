.PHONY: clean pack test

clean:
	rm -rf dist/*

pack:
	python setup.py sdist bdist_wheel

test:
	python -m unittest discover tests
