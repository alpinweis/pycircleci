# pycircleci

[![PyPI version](https://badge.fury.io/py/pycircleci.svg)](https://badge.fury.io/py/pycircleci)
[![Build Status](https://travis-ci.org/alpinweis/pycircleci.svg?branch=master)](https://travis-ci.org/alpinweis/pycircleci)

Python client for [CircleCI API](https://circleci.com/docs/2.0/api-intro/).

Based on the discontinued [circleci.py](https://github.com/levlaz/circleci.py) project.

Original Author & Credit: Lev Lazinskiy (https://levlaz.org)

## Features

- Supports [API v1.1](https://circleci.com/docs/api/#api-overview) and [API v2](https://circleci.com/docs/api/v2/)
- Supports both `circleci.com` and self-hosted [Enterprise CircleCI](https://circleci.com/enterprise/)

## Installation

    $ pip install pycircleci

## Usage

Create a personal [API token](https://circleci.com/docs/2.0/managing-api-tokens/#creating-a-personal-api-token).

```python
    from pycircleci.api import Api

    circleci = Api(YOUR_CIRCLECI_TOKEN)

    # get current user info
    circleci.get_user_info()

    # get list of projects
    circleci.get_projects()
```

### Contributing

1. Fork it
2. Create your feature branch (`git checkout -b my-new-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin my-new-feature`)
5. Create new Pull Request
