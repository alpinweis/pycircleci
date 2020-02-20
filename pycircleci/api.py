import os

import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3 import Retry


CIRCLE_TOKEN = os.getenv("CIRCLE_TOKEN")

API_BASE_URL = "https://circleci.com/api"

API_VER_V1 = "v1.1"
API_VER_V2 = "v2"

GET, POST, PUT, DELETE = "GET", "POST", "PUT", "DELETE"

GITHUB = "github"


class CircleciError(Exception):
    pass


class Api:
    """Client for CircleCI API"""

    def __init__(self, token=None, url=API_BASE_URL):
        """Initialize a client to interact with CircleCI API.

        :param token: CircleCI API access token. Defaults to CIRCLE_TOKEN env var
        :param url: The URL of the CircleCI API instance.
            Defaults to https://circleci.com/api. If running a self-hosted
            CircleCI server, the API is available at the ``/api`` endpoint of the
            installation url, i.e. https://circleci.yourcompany.com/api
        """
        token = CIRCLE_TOKEN if token is None else token
        if not token:
            raise CircleciError("Missing or empty CircleCI API access token")

        self.token = token
        self.url = url
        self._session = self._request_session()

    def __repr__(self):
        opts = {
            "token": self.token,
            "url": self.url,
        }
        kwargs = [f"{k}={v!r}" for k, v in opts.items()]
        return f'Api({", ".join(kwargs)})'

    def get_user_info(self):
        """Get info about the signed in user.

        Endpoint:
            GET: ``/me``
        """
        endpoint = "me"
        resp = self._request(GET, endpoint)
        return resp

    def get_project(self, slug):
        """Get a project by its unique slug.

        Endpoint:
            GET: ``/project/:slug``
        """
        endpoint = "project/{0}".format(slug)
        resp = self._request(GET, endpoint, api_version=API_VER_V2)
        return resp

    def get_projects(self):
        """Get list of projects followed.

        Endpoint:
            GET: ``/projects``
        """
        endpoint = "projects"
        resp = self._request(GET, endpoint)
        return resp

    def follow_project(self, username, project, vcs_type=GITHUB):
        """Follow a project.

        :param username: Org or user name.
        :param project: Repo name.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            POST: ``/project/:vcs-type/:username/:project/follow``
        """
        endpoint = "project/{0}/{1}/{2}/follow".format(
            vcs_type,
            username,
            project
        )
        resp = self._request(POST, endpoint)
        return resp

    def get_project_build_summary(
        self,
        username,
        project,
        limit=30,
        offset=0,
        status_filter=None,
        branch=None,
        vcs_type=GITHUB,
        shallow=False,
    ):
        """Get build summary for each of the last 30 builds for a single repo.

        :param username: Org or user name.
        :param project: Repo name.
        :param limit: Number of builds to return. Maximum 100, defaults to 30.
        :param offset: The API returns builds starting from this offset, defaults to 0.
        :param status_filter: Restricts which builds are returned.
            Set to "completed", "successful", "running" or "failed".
            Defaults to None (no filter).
        :param branch: Restricts returned builds to a single branch.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.
        :param shallow: Optional boolean value that may be sent to improve
            overall performance if set to "true".

        :type limit: int
        :type offset: int
        :type shallow: bool

        Endpoint:
            GET: ``/project/:vcs-type/:username/:project``
        """
        valid_filters = [None, "completed", "successful", "failed", "running"]

        if status_filter not in valid_filters:
            raise CircleciError("Invalid status: {}. Valid values are: {}".format(status_filter, valid_filters))

        _shallow = "&shallow=true" if shallow else ""

        if branch:
            endpoint = "project/{0}/{1}/{2}/tree/{3}?limit={4}&offset={5}&filter={6}{7}".format(
                vcs_type,
                username,
                project,
                branch,
                limit,
                offset,
                status_filter,
                _shallow,
            )
        else:
            endpoint = "project/{0}/{1}/{2}?limit={3}&offset={4}&filter={5}{6}".format(
                vcs_type,
                username,
                project,
                limit,
                offset,
                status_filter,
                _shallow,
            )

        resp = self._request(GET, endpoint)
        return resp

    def get_recent_builds(self, limit=30, offset=0, shallow=False):
        """Get build summary for each of the last 30 recent builds, ordered by build_num.

        :param limit: Number of builds to return. Maximum 100, defaults to 30.
        :param offset: The API returns builds starting from this offset, defaults to 0.
        :param shallow: Optional boolean value that may be sent to improve
            overall performance if set to "true".

        :type limit: int
        :type offset: int
        :type shallow: bool

        Endpoint:
            GET: ``/recent-builds``
        """
        _shallow = "&shallow=true" if shallow else ""
        endpoint = "recent-builds?limit={0}&offset={1}{2}".format(limit, offset, _shallow)
        resp = self._request(GET, endpoint)
        return resp

    def get_build_info(self, username, project, build_num, vcs_type=GITHUB):
        """Get full details of a single build.

        :param username: Org or user name.
        :param project: Repo name.
        :param build_num: Build number.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET: ``/project/:vcs-type/:username/:project/:build_num``
        """
        endpoint = "project/{0}/{1}/{2}/{3}".format(
            vcs_type,
            username,
            project,
            build_num,
        )
        resp = self._request(GET, endpoint)
        return resp

    def get_artifacts(self, username, project, build_num, vcs_type=GITHUB):
        """Get list of artifacts produced by a given build.

        :param username: Org or user name.
        :param project: Repo name.
        :param build_num: Build number.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET: ``/project/:vcs-type/:username/:project/:build_num/artifacts``
        """
        endpoint = "project/{0}/{1}/{2}/{3}/artifacts".format(
            vcs_type,
            username,
            project,
            build_num,
        )
        resp = self._request(GET, endpoint)
        return resp

    def get_latest_artifact(
        self,
        username,
        project,
        branch=None,
        status_filter="completed",
        vcs_type=GITHUB,
    ):
        """Get list of artifacts produced by the latest build on a given branch.

        .. note::
            This endpoint is a little bit flakey. If the "latest"
            build does not have any artifacts, rather than returning
            an empty set, the API returns a 404.

        :param username: Org or user name.
        :param project: Repo name.
        :param branch: The branch to look in for the latest build.
            Returns artifacts for latest build in the entire project if omitted.
        :param filter: Restricts which builds are returned. defaults to "completed".
            Valid filters: "completed", "successful", "failed"
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET: ``/project/:vcs-type/:username/:project/latest/artifacts``
        """
        valid_filters = ["completed", "successful", "failed"]

        if status_filter not in valid_filters:
            raise CircleciError("Invalid status: {}. Valid values are: {}".format(status_filter, valid_filters))

        # passing None returns a 404
        if branch:
            endpoint = "project/{0}/{1}/{2}/latest/artifacts?branch={3}&filter={4}".format(
                vcs_type,
                username,
                project,
                branch,
                status_filter,
            )
        else:
            endpoint = "project/{0}/{1}/{2}/latest/artifacts?filter={3}".format(
                vcs_type,
                username,
                project,
                status_filter,
            )

        resp = self._request(GET, endpoint)
        return resp

    def download_artifact(self, url, destdir=None, filename=None):
        """Download an artifact from a url.

        :param url: URL to the artifact.
        :param destdir: Optional destination directory.
            Defaults to None (curent working directory).
        :param filename: Optional file name. Defaults to the name of the artifact file.
        """
        resp = self._download(url, destdir, filename)
        return resp

    def retry_build(self, username, project, build_num, ssh=False, vcs_type=GITHUB):
        """Retries the build.

        :param username: Org or user name.
        :param project: Repo name.
        :param build_num: Build number.
        :param ssh: Retry a build with SSH enabled. Defaults to False.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        :type ssh: bool

        Endpoint:
            POST: ``/project/:vcs-type/:username/:project/:build_num/retry``
        """
        if ssh:
            endpoint = "project/{0}/{1}/{2}/{3}/ssh".format(
                vcs_type,
                username,
                project,
                build_num,
            )
        else:
            endpoint = "project/{0}/{1}/{2}/{3}/retry".format(
                vcs_type,
                username,
                project,
                build_num,
            )

        resp = self._request(POST, endpoint)
        return resp

    def cancel_build(self, username, project, build_num, vcs_type=GITHUB):
        """Cancel a build.

        :param username: Org or user name.
        :param project: Repo name.
        :param build_num: Build number.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            POST: ``/project/:vcs-type/:username/:project/:build_num/cancel``
        """
        endpoint = "project/{0}/{1}/{2}/{3}/cancel".format(
            vcs_type,
            username,
            project,
            build_num,
        )
        resp = self._request(POST, endpoint)
        return resp

    def get_pipeline(self, pipeline_id):
        """Get full details of a given pipeline.

        :param pipeline_id: Pipieline ID.

        Endpoint:
            GET: ``/pipeline/:id``
        """
        endpoint = "pipeline/{0}".format(pipeline_id)
        resp = self._request(GET, endpoint, api_version=API_VER_V2)
        return resp

    def get_pipeline_config(self, pipeline_id):
        """Get the configuration of a given pipeline.

        :param pipeline_id: Pipieline ID.

        Endpoint:
            GET: ``/pipeline/:id/config``
        """
        endpoint = "pipeline/{0}/config".format(pipeline_id)
        resp = self._request(GET, endpoint, api_version=API_VER_V2)
        return resp

    def get_workflow(self, workflow_id):
        """Get summary details of a given workflow.

        :param workflow_id: Workflow ID.

        Endpoint:
            GET: ``/workflow/:id``
        """
        endpoint = "workflow/{0}".format(workflow_id)
        resp = self._request(GET, endpoint, api_version=API_VER_V2)
        return resp

    def get_workflow_jobs(self, workflow_id):
        """Get list of jobs of a given workflow.

        :param workflow_id: Workflow ID.

        Endpoint:
            GET: ``/workflow/:id/job``
        """
        endpoint = "workflow/{0}/job".format(workflow_id)
        resp = self._request(GET, endpoint, api_version=API_VER_V2)
        return resp

    def add_ssh_user(self, username, project, build_num, vcs_type=GITHUB):
        """Adds a user to the build SSH permissions.

        :param username: Org or user name.
        :param project: Repo name.
        :param build_num: Build number.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            POST: ``/project/:vcs-type/:username/:project/:build_num/ssh-users``
        """
        endpoint = "project/{0}/{1}/{2}/{3}/ssh-users".format(
            vcs_type,
            username,
            project,
            build_num,
        )
        resp = self._request(POST, endpoint)
        return resp

    def trigger_build(
        self,
        username,
        project,
        branch="master",
        revision=None,
        tag=None,
        parallel=None,
        params=None,
        vcs_type=GITHUB,
    ):
        """Trigger a new build.

        .. note::
            * ``tag`` and ``revision`` are mutually exclusive.
            * ``parallel`` is ignored for builds running on CircleCI 2.0

        :param username: Organization or user name.
        :param project: Repo name.
        :param branch: The branch to build. Defaults to master.
        :param revision: The specific git revision to build.
            Defaults to None and the head of the branch is used.
            Cannot be used with the ``tag`` parameter.
        :param tag: The git tag to build.
            Defaults to None. Cannot be used with the ``tag`` parameter.
        :param parallel: Number of containers to use to run the build.
            Defaults to None and the project default is used.
        :param params: Optional build parameters.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        :type params: dict
        :type parallel: int

        Endpoint:
            POST: ``project/:vcs-type/:username/:project/tree/:branch``
        """
        data = {
            "parallel": parallel,
            "revision": revision,
            "tag": tag,
        }

        if params:
            data.update(params)

        endpoint = "project/{0}/{1}/{2}/tree/{3}".format(
            vcs_type,
            username,
            project,
            branch,
        )

        resp = self._request(POST, endpoint, data=data)
        return resp

    def add_ssh_key(self, username, project, ssh_key, vcs_type=GITHUB, hostname=None):
        """Create an SSH key.

        Used to access external systems that require SSH key-based authentication.

        .. note::
            The ssh_key must be unencrypted.

        :param username: Org or user name.
        :param project: Repo name.
        :param branch: Branch name. Defaults to master.
        :param ssh_key: Private RSA key.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.
        :param hostname: Optional hostname. If set, the key will only work
            for this hostname.

        Endpoint:
            POST: ``/project/:vcs-type/:username/:project/ssh-key``
        """
        endpoint = "project/{0}/{1}/{2}/ssh-key".format(
            vcs_type,
            username,
            project,
        )

        params = {
            "hostname": hostname,
            "private_key": ssh_key,
        }

        resp = self._request(POST, endpoint, data=params)
        return resp

    def list_checkout_keys(self, username, project, vcs_type=GITHUB):
        """Get list of checkout keys for a project.

        :param username: Org or user name.
        :param project: Repo name.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET: ``project/:vcs-type/:username/:project/checkout-key``
        """
        endpoint = "project/{0}/{1}/{2}/checkout-key".format(
            vcs_type,
            username,
            project,
        )

        resp = self._request(GET, endpoint)
        return resp

    def create_checkout_key(self, username, project, key_type, vcs_type=GITHUB):
        """Create a new checkout key for a project.

        :param username: Org or user name.
        :param project: Repo name.
        :param key_type: Type of key to create. Valid values are:
            "deploy-key" or "github-user-key"
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            POST: ``/project/:vcs-type/:username/:project/checkout-key``
        """
        valid_types = ["deploy-key", "github-user-key"]

        if key_type not in valid_types:
            raise CircleciError("Invalid key type: {}. Valid values are: {}".format(key_type, valid_types))

        params = {"type": key_type}

        endpoint = "project/{0}/{1}/{2}/checkout-key".format(
            vcs_type,
            username,
            project,
        )

        resp = self._request(POST, endpoint, data=params)
        return resp

    def get_checkout_key(self, username, project, fingerprint, vcs_type=GITHUB):
        """Get a checkout key.

        :param username: Org or user name.
        :param project: Repo name.
        :param fingerprint: The fingerprint of the checkout key.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET: ``/project/:vcs-type/:username/:project/checkout-key/:fingerprint``
        """
        endpoint = "project/{0}/{1}/{2}/checkout-key/{3}".format(
            vcs_type,
            username,
            project,
            fingerprint,
        )

        resp = self._request(GET, endpoint)
        return resp

    def delete_checkout_key(self, username, project, fingerprint, vcs_type=GITHUB):
        """Delete a checkout key.

        :param username: Org or user name.
        :param project: Repo name.
        :param fingerprint: The fingerprint of the checkout key.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            DELETE: ``/project/:vcs-type/:username/:project/checkout-key/:fingerprint``
        """
        endpoint = "project/{0}/{1}/{2}/checkout-key/{3}".format(
            vcs_type,
            username,
            project,
            fingerprint,
        )

        resp = self._request(DELETE, endpoint)
        return resp

    def get_test_metadata(self, username, project, build_num, vcs_type=GITHUB):
        """Get test metadata for a build.

        :param username: Org or user name.
        :param project: Repo name.
        :param build_num: Build number.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET: ``/project/:vcs-type/:username/:project/:build_num/tests``
        """
        endpoint = "project/{0}/{1}/{2}/{3}/tests".format(
            vcs_type,
            username,
            project,
            build_num,
        )

        resp = self._request(GET, endpoint)
        return resp

    def list_envvars(self, username, project, vcs_type=GITHUB):
        """Get list of environment variables for a project.

        :param username: Org or user name.
        :param project: Repo name.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET: ``/project/:vcs-type/:username/:project/envvar``
        """
        endpoint = "project/{0}/{1}/{2}/envvar".format(
            vcs_type,
            username,
            project,
        )

        resp = self._request(GET, endpoint)
        return resp

    def add_envvar(self, username, project, name, value, vcs_type=GITHUB):
        """Add an environment variable to project.

        :param username: Org or user name.
        :param project: Repo name.
        :param name: Name of the environment variable.
        :param value: Value of the environment variable.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            POST: ``/project/:vcs-type/:username/:project/envvar``
        """
        params = {
            "name": name,
            "value": value,
        }

        endpoint = "project/{0}/{1}/{2}/envvar".format(
            vcs_type,
            username,
            project
        )

        resp = self._request(POST, endpoint, data=params)
        return resp

    def get_envvar(self, username, project, name, vcs_type=GITHUB):
        """Get the hidden value of an environment variable.

        :param username: Org or user name.
        :param project: Repo name.
        :param name: Name of the environment variable.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET ``/project/:vcs-type/:username/:project/envvar/:name``
        """
        endpoint = "project/{0}/{1}/{2}/envvar/{3}".format(
            vcs_type,
            username,
            project,
            name,
        )

        resp = self._request(GET, endpoint)
        return resp

    def delete_envvar(self, username, project, name, vcs_type=GITHUB):
        """Delete an environment variable.

        :param username: Org or user name.
        :param project: Repo name.
        :param name: Name of the environment variable.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            DELETE ``/project/:vcs-type/:username/:project/envvar/:name``
        """
        endpoint = "project/{0}/{1}/{2}/envvar/{3}".format(
            vcs_type,
            username,
            project,
            name,
        )

        resp = self._request(DELETE, endpoint)
        return resp

    def get_project_settings(self, username, project, vcs_type=GITHUB):
        """Get project advanced settings.

        :param username: Org or user name.
        :param project: Repo name.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET ``/project/:vcs-type/:username/:project/settings``
        """
        endpoint = "project/{0}/{1}/{2}/settings".format(
            vcs_type,
            username,
            project,
        )

        resp = self._request(GET, endpoint)
        return resp

    def update_project_settings(self, username, project, settings, vcs_type=GITHUB):
        """Update project advanced settings.

        :param username: Org or user name.
        :param project: Repo name.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.
        :param settings: Settings to update.
            Refer to mocks/get_project_settings_response for example settings.

        :type settings: dict

        Endpoint:
            PUT ``/project/:vcs-type/:username/:project/settings``
        """
        endpoint = "project/{0}/{1}/{2}/settings".format(
            vcs_type,
            username,
            project,
        )

        resp = self._request(PUT, endpoint, data=settings)
        return resp

    def _request_session(
        self,
        retries=3,
        backoff_factor=0.3,
        status_forcelist=(408, 500, 502, 503, 504, 520, 521, 522, 523, 524),
    ):
        """Get a session with Retry enabled.

        :param retries: Number of retries to allow.
        :param backoff_factor: Backoff factor to apply between attempts.
        :param status_forcelist: HTTP status codes to force a retry on.

        :returns: A requests.Session object.
        """
        session = requests.Session()
        retry = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            method_whitelist=False,
            raise_on_redirect=False,
            raise_on_status=False,
            respect_retry_after_header=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _request(self, verb, endpoint, data=None, api_version=None):
        """Send an HTTP request.

        :param verb: HTTP method. GET, POST or DELETE.
        :param endpoint: API endpoint to call.
        :param data: Optional POST data.
        :param api_version: Optional API version to use. Defaults to v1.1

        :type data: dict

        :raises requests.exceptions.HTTPError: When response code is not successful.

        :returns: A JSON object with the response from the API.
        """

        verbs = [GET, POST, PUT, DELETE]

        headers = {"Accept": "application/json"}
        auth = HTTPBasicAuth(self.token, "")
        resp = None

        api_version = API_VER_V1 if api_version is None else api_version
        request_url = "{0}/{1}/{2}".format(self.url, api_version, endpoint)

        if verb == GET:
            resp = self._session.get(request_url, auth=auth, headers=headers)
        elif verb == POST:
            resp = self._session.post(request_url, auth=auth, headers=headers, json=data)
        elif verb == PUT:
            resp = self._session.put(request_url, auth=auth, headers=headers, json=data)
        elif verb == DELETE:
            resp = self._session.delete(request_url, auth=auth, headers=headers)
        else:
            raise CircleciError("Invalid verb: {}. Valid values are: {}".format(verb, verbs))

        resp.raise_for_status()
        return resp.json()

    def _download(self, url, destdir=None, filename=None):
        """Download a file.

        :param url: URL to the artifact.
        :param destdir: Optional destination directory.
            Defaults to None (curent working directory).
        :param filename: Optional file name. Defaults to the name of the artifact file.
        """
        if not filename:
            filename = url.split("/")[-1]

        if not destdir:
            destdir = os.getcwd()

        endpoint = "{0}?circle-token={1}".format(url, self.token)

        resp = self._session.get(endpoint, stream=True)

        path = "{0}/{1}".format(destdir, filename)

        with open(path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        return path
