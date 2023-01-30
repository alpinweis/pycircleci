import json
import os

import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from requests_toolbelt.utils import dump
from urllib3 import Retry

API_BASE_URL = "https://circleci.com/api"

CIRCLE_TOKEN = os.getenv("CIRCLE_TOKEN")
CIRCLE_API_URL = os.getenv("CIRCLE_API_URL", API_BASE_URL)
CIRCLE_API_KEY_HEADER = "Circle-Token"

API_VER_V1 = "v1.1"
API_VER_V2 = "v2"
API_VERSIONS = [API_VER_V1, API_VER_V2]

DELETE, GET, PATCH, POST, PUT = HTTP_METHODS = ["DELETE", "GET", "PATCH", "POST", "PUT"]

BITBUCKET = "bitbucket"  # bb
GITHUB = "github"  # gh
ORG = "organization"


class CircleciError(Exception):
    pass


class Api:
    """Client for CircleCI API"""

    def __init__(self, token=None, url=None):
        """Initialize a client to interact with CircleCI API.

        :param token: CircleCI API access token. Defaults to CIRCLE_TOKEN env var
        :param url: The URL of the CircleCI API instance.
            Defaults to https://circleci.com/api. If running a self-hosted
            CircleCI server, the API is available at the ``/api`` endpoint of the
            installation url, i.e. https://circleci.yourcompany.com/api
        """
        url = CIRCLE_API_URL if url is None else url
        token = CIRCLE_TOKEN if token is None else token
        if not token:
            raise CircleciError("Missing or empty CircleCI API access token")

        self.token = token
        self.url = url
        self._session = self._request_session()
        self.last_response = None

    def __repr__(self):
        opts = {"token": self.token, "url": self.url}
        kwargs = [f"{k}={v!r}" for k, v in opts.items()]
        return f'Api({", ".join(kwargs)})'

    def ppj(self, data):
        """Pretty print data as json"""
        print(json.dumps(data, indent=2))

    def ppr(self, resp=None):
        """Pretty print the last request/response details"""
        resp = self.last_response if resp is None else resp
        if resp:
            data = dump.dump_all(resp)
            print(data.decode("utf-8", "ignore"))

    def get_user_info(self, api_version=None):
        """Get info about the signed in user.

        :param api_version: Optional API version. Defaults to v1.1

        Endpoint:
            GET ``/me``
        """
        endpoint = "me"
        resp = self._request(GET, endpoint, api_version=api_version)
        return resp

    # alias for get_user_info()
    me = get_user_info

    def get_user_id_info(self, user_id):
        """Get info about the user with a given ID.

        Endpoint:
            GET ``/user/:user-id``
        """
        endpoint = "user/{0}".format(user_id)
        resp = self._request(GET, endpoint, api_version=API_VER_V2)
        return resp

    def get_user_collaborations(self):
        """Get the set of organizations of which a user is a member or a collaborator.

        Endpoint:
            GET ``/me/collaborations``
        """
        endpoint = "me/collaborations"
        resp = self._request(GET, endpoint, api_version=API_VER_V2)
        return resp

    def get_user_repos(self, vcs_type=GITHUB, paginate=False, limit=None):
        """Get list of repos accessible to the user.

        .. note::
            This is useful because ``get_projects`` only shows projects a user
            is following, and ``get_project`` can show a project as existing
            even if it isn't currently setup.

        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.
        :param paginate: If True, repeatedly requests more items from the endpoint until the limit has been reached (or until all results have been fetched). Defaults to False.
        :param limit: Maximum number of items to return. By default returns all the results from multiple calls to the endpoint, or all the results from a single call to the endpoint, depending on the value for ``paginate``.

        Endpoint:
            GET ``/user/repos/:vcs-type``
        """
        endpoint = "/user/repos/{0}".format(vcs_type)

        resp = self._request_get_items(endpoint, api_version=API_VER_V1,  paginate=paginate, limit=limit)
        return resp

    def get_project(self, slug):
        """Get a project by project slug.

        :param slug: Project slug.

        Endpoint:
            GET ``/project/:slug``
        """
        endpoint = "project/{0}".format(slug)
        resp = self._request(GET, endpoint, api_version=API_VER_V2)
        return resp

    def get_projects(self):
        """Get list of projects followed.

        Endpoint:
            GET ``/projects``
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
            POST ``/project/:vcs-type/:username/:project/follow``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/follow".format(slug)
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
            GET ``/project/:vcs-type/:username/:project``
        """
        valid_filters = ["completed", "successful", "failed", "running", None]
        if status_filter not in valid_filters:
            raise CircleciError("Invalid status: {}. Valid values are: {}".format(status_filter, valid_filters))

        params = {"limit": limit, "offset": offset}

        if status_filter:
            params["filter"] = status_filter
        if shallow:
            params["shallow"] = True

        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}".format(slug)
        if branch:
            endpoint += "/tree/{0}".format(branch)
        resp = self._request(GET, endpoint, params=params)
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
            GET ``/recent-builds``
        """
        params = {"limit": limit, "offset": offset}

        if shallow:
            params["shallow"] = True

        endpoint = "recent-builds"
        resp = self._request(GET, endpoint, params=params)
        return resp

    def get_build_info(self, username, project, build_num, vcs_type=GITHUB):
        """Get full details of a single build.

        :param username: Org or user name.
        :param project: Repo name.
        :param build_num: Build number.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET ``/project/:vcs-type/:username/:project/:build-num``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/{1}".format(slug, build_num)
        resp = self._request(GET, endpoint)
        return resp

    def get_artifacts(self, username, project, build_num, vcs_type=GITHUB):
        """Get list of artifacts produced by a given build.

        :param username: Org or user name.
        :param project: Repo name.
        :param build_num: Build number.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET ``/project/:vcs-type/:username/:project/:build-num/artifacts``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/{1}/artifacts".format(slug, build_num)
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
        :param filter: Restricts which builds are returned. Defaults to "completed".
            Valid filters: "completed", "successful", "failed"
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET ``/project/:vcs-type/:username/:project/latest/artifacts``
        """
        valid_filters = ["completed", "successful", "failed"]
        if status_filter not in valid_filters:
            raise CircleciError("Invalid status: {}. Valid values are: {}".format(status_filter, valid_filters))

        params = {"filter": status_filter}

        if branch:
            params["branch"] = branch

        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/latest/artifacts".format(slug)
        resp = self._request(GET, endpoint, params=params)
        return resp

    def download_artifact(self, url, destdir=None, filename=None):
        """Download an artifact from a url.

        :param url: URL to the artifact.
        :param destdir: Destination directory. Defaults to None (current working directory).
        :param filename: File name. Defaults to the name of the artifact file.
        """
        resp = self._download(url, destdir, filename)
        return resp

    def get_test_metadata(self, username, project, build_num, vcs_type=GITHUB):
        """Get test metadata for a build.

        :param username: Org or user name.
        :param project: Repo name.
        :param build_num: Build number.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET ``/project/:vcs-type/:username/:project/:build-num/tests``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/{1}/tests".format(slug, build_num)
        resp = self._request(GET, endpoint)
        return resp

    def retry_build(self, username, project, build_num, ssh=False, vcs_type=GITHUB):
        """Retry a build.

        :param username: Org or user name.
        :param project: Repo name.
        :param build_num: Build number.
        :param ssh: Retry a build with SSH enabled. Defaults to False.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        :type ssh: bool

        Endpoint:
            POST ``/project/:vcs-type/:username/:project/:build-num/{retry|ssh}``
        """
        action = "ssh" if ssh else "retry"
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/{1}/{2}".format(slug, build_num, action)
        resp = self._request(POST, endpoint)
        return resp

    def cancel_build(self, username, project, build_num, vcs_type=GITHUB):
        """Cancel a build.

        :param username: Org or user name.
        :param project: Repo name.
        :param build_num: Build number.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            POST ``/project/:vcs-type/:username/:project/:build-num/cancel``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/{1}/cancel".format(slug, build_num)
        resp = self._request(POST, endpoint)
        return resp

    def get_job_details(self, username, project, job_number, vcs_type=GITHUB):
        """Get job details.

        :param username: Org or user name.
        :param project: Repo name.
        :param job_number: Job number
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET ``/project/:vcs-type/:username/:project/job/:job-number``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/job/{1}".format(slug, job_number)
        resp = self._request(GET, endpoint, api_version=API_VER_V2)
        return resp

    def cancel_job(self, username, project, job_number, vcs_type=GITHUB):
        """Cancel a job.

        :param username: Org or user name.
        :param project: Repo name.
        :param job_number: Job number.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            POST ``/project/:vcs-type/:username/:project/job/:job-number/cancel``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/job/{1}/cancel".format(slug, job_number)
        resp = self._request(POST, endpoint, api_version=API_VER_V2)
        return resp

    def get_project_pipelines(self, username, project, branch=None, mine=False, vcs_type=GITHUB, paginate=False, limit=None):
        """Get all pipelines configured for a project.

        :param username: Org or user name.
        :param project: Repo name.
        :param branch: Restricts returned pipelines to a single branch. Ignored if ``mine`` is True.
        :param mine: Restricts returned results to pipelines triggered by the current user. Defaults to False.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.
        :param paginate: If True, repeatedly requests more items from the endpoint until the limit has been reached (or until all results have been fetched). Defaults to False.
        :param limit: Maximum number of items to return. By default returns all the results from multiple calls to the endpoint, or all the results from a single call to the endpoint, depending on the value for ``paginate``.

        Endpoint:
            GET ``/project/:vcs-type/:username/:project/pipeline``
        """
        params = {"branch": branch} if branch else None

        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/pipeline".format(slug)
        if mine:
            endpoint += "/mine"
        resp = self._request_get_items(endpoint, params=params, paginate=paginate, limit=limit)
        return resp

    def get_project_pipeline(self, username, project, pipeline_num, vcs_type=GITHUB):
        """Get full details of a given project pipeline by pipeline number.

        :param username: Org or user name.
        :param project: Repo name.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.
        :param pipeline_num: Pipeline number

        Endpoint:
            GET ``/project/:vcs-type/:username/:project/pipeline/:pipeline-number``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/pipeline/{1}".format(slug, pipeline_num)
        resp = self._request(GET, endpoint, api_version=API_VER_V2)
        return resp

    def continue_pipeline(self, continuation_key, config, params=None):
        """Continue a pipeline from the setup phase.

        :param continuation_key: Pipeline continuation key.
        :param config: Configuration string for the pipeline.
        :param params: Optional query parameters.

        :type params: dict

        Endpoint:
            POST ``/pipeline/continue``
        """
        data = {"continuation-key": continuation_key, "configuration": config}

        if params:
            data["parameters"] = params

        endpoint = "pipeline/continue"
        resp = self._request(POST, endpoint, data=data, api_version=API_VER_V2)
        return resp

    def get_pipelines(self, username, mine=False, vcs_type=GITHUB, paginate=False, limit=None):
        """Get all pipelines for the most recently built projects (max 250) you follow in an org.

        :param username: Org or user name.
        :param mine: Only include entries created by your user. Defaults to False.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.
        :param paginate: If True, repeatedly requests more items from the endpoint until the limit has been reached (or until all results have been fetched). Defaults to False.
        :param limit: Maximum number of items to return. By default returns all the results from multiple calls to the endpoint, or all the results from a single call to the endpoint, depending on the value for ``paginate``.

        Endpoint:
            GET ``/pipeline``
        """
        params = {"org-slug": self.owner_slug(username, vcs_type)}
        if mine:
            params["mine"] = True

        endpoint = "pipeline"
        resp = self._request_get_items(endpoint, params=params, paginate=paginate, limit=limit)
        return resp

    def get_pipeline(self, pipeline_id):
        """Get full details of a given pipeline.

        :param pipeline_id: Pipieline ID.

        Endpoint:
            GET ``/pipeline/:pipeline-id``
        """
        endpoint = "pipeline/{0}".format(pipeline_id)
        resp = self._request(GET, endpoint, api_version=API_VER_V2)
        return resp

    def get_pipeline_config(self, pipeline_id):
        """Get the configuration of a given pipeline.

        :param pipeline_id: Pipieline ID.

        Endpoint:
            GET ``/pipeline/:pipeline-id/config``
        """
        endpoint = "pipeline/{0}/config".format(pipeline_id)
        resp = self._request(GET, endpoint, api_version=API_VER_V2)
        return resp

    def get_pipeline_workflow(self, pipeline_id, paginate=False, limit=None):
        """Get the workflow of a given pipeline.

        :param pipeline_id: Pipieline ID.
        :param paginate: If True, repeatedly requests more items from the endpoint until the limit has been reached (or until all results have been fetched). Defaults to False.
        :param limit: Maximum number of items to return. By default returns all the results from multiple calls to the endpoint, or all the results from a single call to the endpoint, depending on the value for ``paginate``.

        Endpoint:
            GET ``/pipeline/:pipeline-id/workflow``
        """
        endpoint = "pipeline/{0}/workflow".format(pipeline_id)
        resp = self._request_get_items(endpoint, paginate=paginate, limit=limit)
        return resp

    def get_workflow(self, workflow_id):
        """Get summary details of a given workflow.

        :param workflow_id: Workflow ID.

        Endpoint:
            GET ``/workflow/:workflow-id``
        """
        endpoint = "workflow/{0}".format(workflow_id)
        resp = self._request(GET, endpoint, api_version=API_VER_V2)
        return resp

    def get_workflow_jobs(self, workflow_id, paginate=False, limit=None):
        """Get list of jobs of a given workflow.

        :param workflow_id: Workflow ID.
        :param paginate: If True, repeatedly requests more items from the endpoint until the limit has been reached (or until all results have been fetched). Defaults to False.
        :param limit: Maximum number of items to return. By default returns all the results from multiple calls to the endpoint, or all the results from a single call to the endpoint, depending on the value for ``paginate``.

        Endpoint:
            GET ``/workflow/:workflow-id/job``
        """
        endpoint = "workflow/{0}/job".format(workflow_id)
        resp = self._request_get_items(endpoint, paginate=paginate, limit=limit)
        return resp

    def cancel_workflow(self, workflow_id):
        """Cancel a workflow.

        :param workflow_id: Workflow ID.

        Endpoint:
            POST ``/workflow/:workflow-id/cancel``
        """
        endpoint = "workflow/{0}/cancel".format(workflow_id)
        resp = self._request(POST, endpoint, api_version=API_VER_V2)
        return resp

    def rerun_workflow(self, workflow_id, jobs=None, from_failed=False, sparse_tree=False):
        """Rerun a workflow.

        :param workflow_id: Workflow ID.
        :param jobs: List of job UUIDs to rerun.
        :param from_failed: Whether to rerun the workflow from the failed job. Mutually exclusive with the ``jobs`` parameter.
        :param sparse_tree: Completes rerun using sparse trees logic. Requires ``jobs`` parameter and so is mutually exclusive with the ``from_failed`` parameter.

        Endpoint:
            POST ``/workflow/:workflow-id/rerun``
        """
        data = {"from_failed": from_failed, "sparse_tree": sparse_tree}
        if jobs:
            data["jobs"] = jobs

        endpoint = "workflow/{0}/rerun".format(workflow_id)
        resp = self._request(POST, endpoint, data=data, api_version=API_VER_V2)
        return resp

    def approve_job(self, workflow_id, approval_request_id):
        """Approve a pending approval job in a workflow.

        :param workflow_id: Workflow ID.
        :param approval_request_id: The ID of the job being approved.

        Endpoint:
            POST ``/workflow/:workflow-id/approve/:approval-request-id``
        """
        endpoint = "workflow/{0}/approve/{1}".format(workflow_id, approval_request_id)
        resp = self._request(POST, endpoint, api_version=API_VER_V2)
        return resp

    def add_ssh_user(self, username, project, build_num, vcs_type=GITHUB):
        """Add a user to the build SSH permissions.

        :param username: Org or user name.
        :param project: Repo name.
        :param build_num: Build number.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            POST ``/project/:vcs-type/:username/:project/:build-num/ssh-users``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/{1}/ssh-users".format(slug, build_num)
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
            Defaults to None. Cannot be used with the ``revision`` parameter.
        :param parallel: Number of containers to use to run the build.
            Defaults to None and the project default is used.
        :param params: Optional build parameters.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        :type params: dict
        :type parallel: int

        Endpoint:
            POST ``/project/:vcs-type/:username/:project/tree/:branch``
        """
        data = {"parallel": parallel, "revision": revision, "tag": tag}

        if params:
            data.update(params)

        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/tree/{1}".format(slug, branch)
        resp = self._request(POST, endpoint, data=data)
        return resp

    def trigger_pipeline(
        self,
        username,
        project,
        branch=None,
        tag=None,
        params=None,
        vcs_type=GITHUB,
    ):
        """Trigger a new pipeline.

        .. note::
            * ``tag`` and ``branch`` are mutually exclusive.

        :param username: Organization or user name.
        :param project: Repo name.
        :param branch: The branch to build.
            Defaults to None. Cannot be used with the ``tag`` parameter.
        :param tag: The git tag to build.
            Defaults to None. Cannot be used with the ``branch`` parameter.
        :param params: Optional build parameters.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        :type params: dict

        Endpoint:
            POST ``/project/:vcs-type/:username/:project/pipeline``
        """
        data = {}
        if branch:
            data["branch"] = branch
        elif tag:
            data["tag"] = tag

        if params:
            data["parameters"] = params

        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/pipeline".format(slug)
        resp = self._request(POST, endpoint, data=data, api_version=API_VER_V2)
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
        :param hostname: Optional hostname. If set, the key will only work for this hostname.

        Endpoint:
            POST ``/project/:vcs-type/:username/:project/ssh-key``
        """
        params = {"hostname": hostname, "private_key": ssh_key}

        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/ssh-key".format(slug)
        resp = self._request(POST, endpoint, data=params)
        return resp

    def list_checkout_keys(self, username, project, vcs_type=GITHUB):
        """Get list of checkout keys for a project.

        :param username: Org or user name.
        :param project: Repo name.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET ``/project/:vcs-type/:username/:project/checkout-key``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/checkout-key".format(slug)
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
            POST ``/project/:vcs-type/:username/:project/checkout-key``
        """
        valid_types = ["deploy-key", "github-user-key"]
        if key_type not in valid_types:
            raise CircleciError("Invalid key type: {}. Valid values are: {}".format(key_type, valid_types))

        params = {"type": key_type}

        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/checkout-key".format(slug)
        resp = self._request(POST, endpoint, data=params)
        return resp

    def get_checkout_key(self, username, project, fingerprint, vcs_type=GITHUB):
        """Get a checkout key.

        :param username: Org or user name.
        :param project: Repo name.
        :param fingerprint: The fingerprint of the checkout key.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET ``/project/:vcs-type/:username/:project/checkout-key/:fingerprint``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/checkout-key/{1}".format(slug, fingerprint)
        resp = self._request(GET, endpoint)
        return resp

    def delete_checkout_key(self, username, project, fingerprint, vcs_type=GITHUB):
        """Delete a checkout key.

        :param username: Org or user name.
        :param project: Repo name.
        :param fingerprint: The fingerprint of the checkout key.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            DELETE ``/project/:vcs-type/:username/:project/checkout-key/:fingerprint``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/checkout-key/{1}".format(slug, fingerprint)
        resp = self._request(DELETE, endpoint)
        return resp

    def list_envvars(self, username, project, vcs_type=GITHUB):
        """Get list of environment variables for a project.

        :param username: Org or user name.
        :param project: Repo name.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET ``/project/:vcs-type/:username/:project/envvar``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/envvar".format(slug)
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
            POST ``/project/:vcs-type/:username/:project/envvar``
        """
        data = {"name": name, "value": value}

        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/envvar".format(slug)
        resp = self._request(POST, endpoint, data=data)
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
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/envvar/{1}".format(slug, name)
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
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/envvar/{1}".format(slug, name)
        resp = self._request(DELETE, endpoint)
        return resp

    def get_contexts(self, username=None, owner_id=None, owner_type=ORG, vcs_type=GITHUB, paginate=False, limit=None):
        """Get contexts for an organization.

        :param username: Org or user name.
        :param owner_id: UUID of owner (use either ``username`` or ``owner_id``).
        :param owner_type: Either ``organization`` or ``account``. Defaults to ``organization``.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.
        :param paginate: If True, repeatedly requests more items from the endpoint until the limit has been reached (or until all results have been fetched). Defaults to False..
        :param limit: Maximum number of items to return. By default returns all the results from multiple calls to the endpoint, or all the results from a single call to the endpoint, depending on the value for ``paginate``.

        Endpoint:
            GET ``/context``
        """
        params = {"owner-type": owner_type}

        if username:
            params["owner-slug"] = self.owner_slug(username, vcs_type)
        elif owner_id:
            params["owner-id"] = owner_id

        endpoint = "context"
        resp = self._request_get_items(endpoint, params=params, paginate=paginate, limit=limit)
        return resp

    def get_context(self, context_id):
        """Get a context.

        :param context_id: UUID of context to get.

        Endpoint:
            GET ``/context/:context-id``
        """
        endpoint = "context/{0}".format(context_id)
        resp = self._request(GET, endpoint, api_version=API_VER_V2)
        return resp

    def add_context(self, name, username=None, owner_id=None, owner_type=ORG, vcs_type=GITHUB):
        """Add a new context at org or account level.

        :param name: Context name to add.
        :param username: Org or user name.
        :param owner_id: UUID of owner (use either ``username`` or ``owner_id``).
        :param owner_type: Either ``organization`` or ``account``. Defaults to ``organization``.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            POST ``/context``
        """
        data = {"name": name, "owner":  {"type": owner_type}}

        if username:
            data["owner"]["slug"] = self.owner_slug(username, vcs_type)
        elif owner_id:
            data["owner"]["id"] = owner_id

        endpoint = "context"
        resp = self._request(POST, endpoint, data=data, api_version=API_VER_V2)
        return resp

    def delete_context(self, context_id):
        """Delete a context.

        :param context_id: UUID of context to delete.

        Endpoint:
            DELETE ``/context/:context-id``
        """
        endpoint = "context/{0}".format(context_id)
        resp = self._request(DELETE, endpoint, api_version=API_VER_V2)
        return resp

    def get_context_envvars(self, context_id, paginate=False, limit=None):
        """Get environment variables for a context.

        :param context_id: ID of context to retrieve environment variables from.
        :param paginate: If True, repeatedly requests more items from the endpoint until the limit has been reached (or until all results have been fetched). Defaults to False..
        :param limit: Maximum number of items to return. By default returns all the results from multiple calls to the endpoint, or all the results from a single call to the endpoint, depending on the value for ``paginate``.

        Endpoint:
            GET ``/context/:context-id/environment-variable``
        """
        endpoint = "context/{0}/environment-variable".format(context_id)
        resp = self._request_get_items(endpoint, paginate=paginate, limit=limit)
        return resp

    def add_context_envvar(self, context_id, name, value):
        """Add or update an environment variable to a context.

        :param context_id: ID of the context to add environment variable to.
        :param name: Name of the environment variable.
        :param value: Value of the environment variable.

        Endpoint:
            PUT ``/context/:context-id/environment-variable/:name``
        """
        data = {"value": value}
        endpoint = "context/{0}/environment-variable/{1}".format(context_id, name)
        resp = self._request(PUT, endpoint, api_version=API_VER_V2, data=data)
        return resp

    def delete_context_envvar(self, context_id, name):
        """Delete an environment variable from a context.

        :param context_id: ID of the context to delete environment variable from.
        :param name: Name of the environment variable.

        Endpoint:
            DELETE ``/context/:context-id/environment-variable/:name``
        """
        endpoint = "context/{0}/environment-variable/{1}".format(context_id, name)
        resp = self._request(DELETE, endpoint, api_version=API_VER_V2)
        return resp

    def get_project_settings(self, username, project, vcs_type=GITHUB):
        """Get project advanced settings.

        :param username: Org or user name.
        :param project: Repo name.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET ``/project/:vcs-type/:username/:project/settings``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/settings".format(slug)
        resp = self._request(GET, endpoint)
        return resp

    def update_project_settings(self, username, project, settings, vcs_type=GITHUB):
        """Update project advanced settings.

        :param username: Org or user name.
        :param project: Repo name.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.
        :param settings: Settings to update.
            Refer to mocks/get_project_settings_response.json for example settings.

        :type settings: dict

        Endpoint:
            PUT ``/project/:vcs-type/:username/:project/settings``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/settings".format(slug)
        resp = self._request(PUT, endpoint, data=settings)
        return resp

    def get_project_branches(self, username, project, workflow_name=None, vcs_type=GITHUB):
        """Get all branches for a given project. The list will only contain branches currently available within Insights.

        :param username: Org or user name.
        :param project: Repo name.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET ``/insights/:vcs-type/:username/:project/branches``
        """
        params = {"workflow-name": workflow_name} if workflow_name else None

        slug = self.project_slug(username, project, vcs_type)
        endpoint = "insights/{0}/branches".format(slug)
        resp = self._request(GET, endpoint, params=params, api_version=API_VER_V2)
        return resp

    def get_project_workflows_metrics(self, username, project, params=None, vcs_type=GITHUB, paginate=False, limit=None):
        """Get summary metrics for a project's workflows.

        :param username: Org or user name.
        :param project: Repo name.
        :param params: Optional query parameters.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.
        :param paginate: If True, repeatedly requests more items from the endpoint until the limit has been reached (or until all results have been fetched). Defaults to False.
        :param limit: Maximum number of items to return. By default returns all the results from multiple calls to the endpoint, or all the results from a single call to the endpoint, depending on the value for ``paginate``.

        Endpoint:
            GET ``/insights/:vcs-type/:username/:project/workflows``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "insights/{0}/workflows".format(slug)
        resp = self._request_get_items(endpoint, params=params, paginate=paginate, limit=limit)
        return resp

    def get_project_workflow_metrics(self, username, project, workflow_name, params=None, vcs_type=GITHUB, paginate=False, limit=None):
        """Get metrics of recent runs of a project workflow.

        :param username: Org or user name.
        :param project: Repo name.
        :param workflow_name: Workflow name
        :param params: Optional query parameters.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.
        :param paginate: If True, repeatedly requests more items from the endpoint until the limit has been reached (or until all results have been fetched). Defaults to False.
        :param limit: Maximum number of items to return. By default returns all the results from multiple calls to the endpoint, or all the results from a single call to the endpoint, depending on the value for ``paginate``.

        Endpoint:
            GET ``/insights/:vcs-type/:username/:project/workflows/:workflow-name``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "insights/{0}/workflows/{1}".format(slug, workflow_name)
        resp = self._request_get_items(endpoint, params=params, paginate=paginate, limit=limit)
        return resp

    def get_project_workflow_test_metrics(self, username, project, workflow_name, params=None, vcs_type=GITHUB):
        """Get test metrics of recent runs of a project workflow.

        :param username: Org or user name.
        :param project: Repo name.
        :param workflow_name: Workflow name
        :param params: Optional query parameters.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET ``/insights/:vcs-type/:username/:project/workflows/:workflow-name/test-metrics``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "insights/{0}/workflows/{1}/test-metrics".format(slug, workflow_name)
        resp = self._request(GET, endpoint, params=params, api_version=API_VER_V2)
        return resp

    def get_project_workflow_jobs_metrics(self, username, project, workflow_name, params=None, vcs_type=GITHUB, paginate=False, limit=None):
        """Get summary metrics for a project workflow's jobs.

        :param username: Org or user name.
        :param project: Repo name.
        :param workflow_name: Workflow name
        :param params: Optional query parameters.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.
        :param paginate: If True, repeatedly requests more items from the endpoint until the limit has been reached (or until all results have been fetched). Defaults to False.
        :param limit: Maximum number of items to return. By default returns all the results from multiple calls to the endpoint, or all the results from a single call to the endpoint, depending on the value for ``paginate``.

        Endpoint:
            GET ``/insights/:vcs-type/:username/:project/workflows/:workflow-name/jobs``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "insights/{0}/workflows/{1}/jobs".format(slug, workflow_name)
        resp = self._request_get_items(endpoint, params=params, paginate=paginate, limit=limit)
        return resp

    def get_project_workflow_job_metrics(self, username, project, workflow_name, job_name, params=None, vcs_type=GITHUB, paginate=False, limit=None):
        """Get metrics of recent runs of a project workflow job.

        :param username: Org or user name.
        :param project: Repo name.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.
        :param workflow_name: Workflow name
        :param job_name: Job name
        :param params: Optional query parameters.
        :param paginate: If True, repeatedly requests more items from the endpoint until the limit has been reached (or until all results have been fetched). Defaults to False.
        :param limit: Maximum number of items to return. By default returns all the results from multiple calls to the endpoint, or all the results from a single call to the endpoint, depending on the value for ``paginate``.

        Endpoint:
            GET ``/insights/:vcs-type/:username/:project/workflows/:workflow-name/jobs/:job-name``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "insights/{0}/workflows/{1}/jobs/{2}".format(slug, workflow_name, job_name)
        resp = self._request_get_items(endpoint, params=params, paginate=paginate, limit=limit)
        return resp

    def get_schedules(self, username, project, vcs_type=GITHUB):
        """Get all schedules for a project.

        :param username: Org or user name.
        :param project: Repo name.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        Endpoint:
            GET ``/project/:vcs-type/:username/:project/schedule``
        """
        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/schedule".format(slug)
        resp = self._request(GET, endpoint, api_version=API_VER_V2)
        return resp

    def get_schedule(self, schedule_id):
        """Get a schedule.

        :param schedule_id: UUID of schedule to get.

        Endpoint:
            GET ``/schedule/:schedule-id``
        """
        endpoint = "schedule/{0}".format(schedule_id)
        resp = self._request(GET, endpoint, api_version=API_VER_V2)
        return resp

    def add_schedule(self, username, project, name, settings, vcs_type=GITHUB):
        """Create a schedule.

        :param username: Org or user name.
        :param project: Repo name.
        :param name: Name of the schedule.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.
        :param settings: Schedule settings.
            Refer to mocks/get_schedule_response.json for example settings.

        :type settings: dict

        Endpoint:
            POST ``/project/:vcs-type/:username/:project/schedule``
        """
        data = {"name": name}
        data.update(settings)

        slug = self.project_slug(username, project, vcs_type)
        endpoint = "project/{0}/schedule".format(slug)
        resp = self._request(POST, endpoint, data=data, api_version=API_VER_V2)
        return resp

    def update_schedule(self, schedule_id, settings):
        """Update a schedule.

        :param schedule_id: UUID of schedule to update.
        :param settings: Schedule settings.
            Refer to mocks/get_schedule_response.json for example settings.

        :type settings: dict

        Endpoint:
            PATCH ``/schedule/:schedule-id``
        """
        endpoint = "schedule/{0}".format(schedule_id)
        resp = self._request(PATCH, endpoint, data=settings, api_version=API_VER_V2)
        return resp

    def delete_schedule(self, schedule_id):
        """Delete a schedule.

        :param schedule_id: UUID of schedule to delete.

        Endpoint:
            DELETE ``/schedule/:schedule-id``
        """
        endpoint = "schedule/{0}".format(schedule_id)
        resp = self._request(DELETE, endpoint, api_version=API_VER_V2)
        return resp

    def project_slug(self, username, reponame, vcs_type=GITHUB):
        """Get project slug.

        :param username: Org or user name.
        :param reponame: Repo name.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        :returns: string ``:vcs-type/:username/:reponame``
        """
        slug = "{0}/{1}/{2}".format(vcs_type, username, reponame)
        return slug

    def owner_slug(self, username, vcs_type=GITHUB):
        """Get owner/org slug.

        :param username: Org or user name.
        :param vcs_type: VCS type (github, bitbucket). Defaults to ``github``.

        :returns: string ``:vcs-type/:username"``
        """
        slug = "{0}/{1}".format(vcs_type, username)
        return slug

    def split_project_slug(self, slug):
        """Split project slug into components.

        :param slug: Project slug.

        :returns: tuple ``(:vcs-type, :username, :reponame)``
        """
        parts = slug.split("/")
        if len(parts) != 3:
            raise CircleciError("Invalid project slug: '{}'".format(slug))
        return tuple(parts)

    def validate_api_version(self, api_version=None):
        """Validate and normalize an API version value"""
        api_version = API_VER_V1 if api_version is None else api_version
        ver = str(api_version).lower()
        if ver in [API_VER_V1, "v1", "1.1", "1", "1.0"]:
            return API_VER_V1
        if ver in [API_VER_V2, "2", "2.0"]:
            return API_VER_V2
        raise CircleciError("Invalid CircleCI API version: {}. Valid values are: {}".format(api_version, API_VERSIONS))

    def _request_session(
        self,
        retries=3,
        backoff_factor=0.3,
        status_forcelist=(408, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524),
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
            allowed_methods=False,
            raise_on_redirect=False,
            raise_on_status=False,
            respect_retry_after_header=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _request(self, verb, endpoint, data=None, params=None, api_version=None):
        """Send an HTTP request.

        :param verb: HTTP method: DELETE, GET, PATCH, POST, PUT
        :param endpoint: API endpoint to call.
        :param data: Optional POST data.
        :param params: Optional query parameters.
        :param api_version: Optional API version. Defaults to v1.1

        :type data: dict
        :type params: dict

        :raises requests.exceptions.HTTPError: When response code is not successful.

        :returns: A JSON object with the response from the API.
        """
        headers = {"Accept": "application/json", "Circle-Token": self.token}
        auth = HTTPBasicAuth(self.token, "")
        resp = None

        api_version = self.validate_api_version(api_version)
        request_url = "{0}/{1}/{2}".format(self.url, api_version, endpoint)

        verb = verb.upper()
        if verb == GET:
            resp = self._session.get(request_url, params=params, auth=auth, headers=headers)
        elif verb == POST:
            resp = self._session.post(request_url, params=params, auth=auth, headers=headers, json=data)
        elif verb == PUT:
            resp = self._session.put(request_url, params=params, auth=auth, headers=headers, json=data)
        elif verb == PATCH:
            resp = self._session.patch(request_url, params=params, auth=auth, headers=headers, json=data)
        elif verb == DELETE:
            resp = self._session.delete(request_url, params=params, auth=auth, headers=headers)
        else:
            raise CircleciError("Invalid HTTP method: {}. Valid values are: {}".format(verb, HTTP_METHODS))

        self.last_response = resp
        resp.raise_for_status()
        return resp.json()

    def _request_get_items(self, endpoint, params=None, api_version=API_VER_V2, paginate=False, limit=None):
        """Send one or more HTTP GET requests and optionally depaginate results, up to a limit.

        :param api_version: API version to use. Defaults to v2
        :param endpoint: API endpoint to GET.
        :param params: Optional query parameters.
        :param paginate: If True, repeatedly requests more items from the endpoint until the limit has been reached (or until all results have been fetched). Defaults to False.
        :param limit: Maximum number of items to return. By default returns all the results from multiple calls to the endpoint, or all the results from a single call to the endpoint, depending on the value for ``paginate``.

        :type params: dict

        :raises requests.exceptions.HTTPError: When response code is not successful.

        :returns: A list of items which are the combined results of the requests made.
        """
        results = []
        page = 1
        params = {} if params is None else params.copy()

        if api_version == API_VER_V1:
            # Don't fetch more than limit, but limit to 100 per page max
            params["per-page"] = limit if limit and limit < 100 else 100

        while True:
            resp = self._request(GET, endpoint, params=params, api_version=api_version)
            # Nested with v2 APIs; flat in v1
            items = resp["items"] if "items" in resp else resp
            results.extend(items)

            # Break on first iteration of the loop if we're not paginating, if
            # we have an empty list from resp (v1), or if we've already hit our
            # limit.
            if not paginate or not resp or (limit and len(results) >= limit):
                break

            page += 1
            if api_version == API_VER_V2:
                # Also break early if there's no next page (v2)
                if not resp["next_page_token"]:
                    break
                params["page-token"] = resp["next_page_token"]
            else:
                params["page"] = page

        return results[:limit]

    def _download(self, url, destdir=None, filename=None):
        """Download artifact file by url.

        :param url: URL to the artifact.
        :param destdir: Optional destination directory. Defaults to None (curent working directory).
        :param filename: Optional file name. Defaults to the name of the artifact file.
        """
        destdir = os.getcwd() if destdir is None else destdir
        filename = url.split("/")[-1] if filename is None else filename

        headers = {CIRCLE_API_KEY_HEADER: self.token}
        resp = self._session.get(url, headers=headers, stream=True)

        path = "{0}/{1}".format(destdir, filename)
        with open(path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        return path
