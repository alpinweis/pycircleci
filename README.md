# pycircleci

[![PyPI version](https://img.shields.io/pypi/v/pycircleci?color=blue)](https://python.org/pypi/pycircleci)
[![Build Status](https://github.com/alpinweis/pycircleci/actions/workflows/test.yml/badge.svg?branch=master)](https://github.com/alpinweis/pycircleci/actions/workflows/test.yml?query=branch%3Amaster)

Python client for [CircleCI API](https://circleci.com/docs/2.0/api-intro/).

Based on the discontinued [circleci.py](https://github.com/levlaz/circleci.py) project.

## Features

- Supports [API v1.1](https://circleci.com/docs/api/#api-overview) and [API v2](https://circleci.com/docs/api/v2/)
- Supports both `circleci.com` and self-hosted [Enterprise CircleCI](https://circleci.com/enterprise/)

## Installation

    $ pip install pycircleci

## Usage

Create a personal [API token](https://circleci.com/docs/2.0/managing-api-tokens/#creating-a-personal-api-token).

Set up the expected env vars:

    CIRCLE_TOKEN           # CircleCI API access token
    CIRCLE_API_URL         # CircleCI API base url. Defaults to https://circleci.com/api

```python
from pycircleci.api import Api, CIRCLE_TOKEN, CIRCLE_API_URL

circle_client = Api(token=CIRCLE_TOKEN, url=CIRCLE_API_URL)

# get current user info
circle_client.get_user_info()

# get list of projects
results = circle_client.get_projects()

# pretty print results as json
circle_client.ppj(results)

# pretty print the details of the last request/response
circle_client.ppr()
```

### Interactive development console

     make console

This starts a pre-configured python interactive console which gives you access to a
`client` object - an instance of the `Api` class to play around. From the console
type `man()` to see the help screen.

### Contributing

1. Fork it
1. Install dev dependencies (`pip install -r requirements-dev.txt`)
1. Create your feature branch (`git checkout -b my-new-feature`)
1. Make sure `flake8` and the `pytest` test suite successfully run locally
1. Commit your changes (`git commit -am 'Add some feature'`)
1. Push to the branch (`git push origin my-new-feature`)
1. Create new Pull Request
