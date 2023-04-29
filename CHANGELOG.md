### [0.7.0] - 2023-04-29
* Add endpoint to get flaky tests (API v2)
* Add build system info to comply with PEP-518

### [0.6.1] - 2023-02-04
* Refactor string formatting to use f-strings

### [0.6.0] - 2023-01-30
* Add endpoint to get user repos

### [0.5.2] - 2022-05-26
* Add support for Circle-Token header based auth

### [0.5.1] - 2022-01-30
* Update deprecated Retry option

### [0.5.0] - 2021-11-10
* Add more insights endpoints (API v2)
* Add more pipeline endpoints (API v2)
* Add more user endpoints (API v2)
* Add more workflow endpoints (API v2)
* Add schedule endpoints (API v2)

### [0.4.1] - 2021-11-07
* Fix get_contexts()
* Add endpoints for context environment variables (API v2)

### [0.4.0] - 2021-11-06
* Add context endpoints (API v2)
* Add job details endpoint (API v2)
* Add support for pagination: the results from endpoints that support pagination will come as a list rather than a list under `response["items"]`

### [0.3.2] - 2021-03-30
* Add response code 429 to the list of HTTP status codes to force a retry on

### [0.3.1] - 2020-08-01
* Add job approval endpoint (API v2)

### [0.3.0] - 2020-05-24
* Add endpoints to get project pipelines (API v2)
* Add endpoints to get project insights (API v2)

### [0.2.0] - 2020-02-20
* Add endpoints to get/update project advanced settings

### [0.1.0] - 2020-02-18
* Initial public version
