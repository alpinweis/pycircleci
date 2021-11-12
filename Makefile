.PHONY: clean pack test

clean:
	rm -rf build/ dist/ pycircleci.egg-info/
	find ./ | grep -E "(__pycache__|\.pytest_cache|\.cache|\.pyc|\.pyo$$)" | xargs rm -rf

console:
	python pycircleci/console.py

pack:
	python setup.py sdist bdist_wheel

test:
	pytest -v tests/
