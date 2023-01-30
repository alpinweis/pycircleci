import json
import pytest
from unittest.mock import MagicMock

from pycircleci.api import Api, CircleciError, DELETE, GET, POST, PUT

TEST_ID = "deadbeef-dead-beef-dead-deaddeafbeef"


@pytest.fixture(scope="session")
def cci():
    """Initialize a CircleCI API client"""
    return Api("TOKEN")


def get_mock(api_client, filename):
    """Get a mock response from file"""
    filename = "tests/mocks/{0}".format(filename)
    with open(filename, "r") as f:
        text = f.read()
        resp = json.loads(text)
        api_client._request = MagicMock(return_value=resp)
        # Spy on this, but don't mock its return value
        api_client._request_get_items = MagicMock(wraps=api_client._request_get_items)


def assert_message_accepted(resp):
    assert "Accepted" in resp["message"]


def assert_message_ok(resp):
    assert resp["message"] == "ok"


def test_invalid_http_method(cci):
    with pytest.raises(CircleciError) as ex:
        cci._request("BAD", "dummy")
    assert "Invalid HTTP method: BAD" in str(ex.value)


def test_get_user_info(cci):
    get_mock(cci, "get_user_info_response.json")
    resp = cci.get_user_info()
    assert resp["selected_email"] == "mock+ccie-tester@circleci.com"


def test_get_user_id_info(cci):
    get_mock(cci, "get_user_id_info_response.json")
    resp = cci.get_user_id_info(TEST_ID)
    assert resp["id"] == TEST_ID
    assert resp["name"] == "John"
    assert resp["login"] == "johndoe"


def test_get_user_collaborations(cci):
    get_mock(cci, "get_user_collaborations_response.json")
    resp = cci.get_user_collaborations()
    assert resp[0]["vcs_type"] == "github"
    assert resp[0]["name"] == "johndoe"
    assert resp[1]["vcs_type"] == "github"
    assert resp[1]["name"] == "org1"


def test_get_user_repos(cci):
    get_mock(cci, "get_user_repos_response.json")
    resp = cci.get_user_repos()
    cci._request_get_items.assert_called_once_with(
        "/user/repos/github",
        api_version="v1.1",
        paginate=False,
        limit=None,
    )
    assert len(resp) == 3
    assert resp[0]["vcs_type"] == "github"
    assert resp[0]["name"] == "repo1"
    assert resp[0]["username"] == "foobar"
    assert resp[0]["has_followers"] is False
    assert resp[1]["vcs_type"] == "github"
    assert resp[1]["name"] == "repo2"
    assert resp[1]["has_followers"] is True
    assert resp[2]["username"] == "otherorg"
    assert resp[2]["owner"]["login"] == "otherorg"
    assert resp[2]["has_followers"] is False


def test_get_user_repos_limit(cci):
    get_mock(cci, "get_user_repos_response.json")
    resp = cci.get_user_repos(limit=2)
    assert cci._request_get_items.call_args.args[0] == "/user/repos/github"
    assert len(resp) == 2


def test_get_project(cci):
    get_mock(cci, "get_project_response.json")
    resp = cci.get_project("gh/foo/bar")
    assert resp["slug"] == "gh/foo/bar"
    assert resp["organization_name"] == "foo"
    assert resp["name"] == "bar"
    assert "vcs_info" in resp


def test_get_projects(cci):
    get_mock(cci, "get_projects_response.json")
    resp = cci.get_projects()
    assert resp[0]["vcs_url"] == "MOCK+https://ghe-dev.circleci.com/ccie-tester/testing"


def test_follow_project(cci):
    get_mock(cci, "follow_project_response.json")
    resp = cci.follow_project("ccie-tester", "testing")
    assert resp["mock+following"] is True


def test_get_project_build_summary(cci):
    get_mock(cci, "get_project_build_summary_response.json")
    resp = cci.get_project_build_summary("ccie-tester", "testing")
    assert resp[0]["username"] == "MOCK+ccie-tester"

    # with invalid status filter
    with pytest.raises(CircleciError) as ex:
        cci.get_project_build_summary("ccie-tester", "testing", status_filter="bad")
    assert "Invalid status: bad" in str(ex.value)

    # with branch
    resp = cci.get_project_build_summary("ccie-tester", "testing", branch="master")
    assert resp[0]["username"] == "MOCK+ccie-tester"


def test_get_recent_builds(cci):
    get_mock(cci, "get_recent_builds_response.json")
    resp = cci.get_recent_builds()
    assert resp[0]["reponame"] == "MOCK+testing"


def test_get_build_info(cci):
    get_mock(cci, "get_build_info_response.json")
    resp = cci.get_build_info("ccie-tester", "testing", "1")
    assert resp["reponame"] == "MOCK+testing"


def test_get_artifacts(cci):
    get_mock(cci, "get_artifacts_response.json")
    resp = cci.get_artifacts("ccie-tester", "testing", "1")
    assert resp[0]["path"] == "MOCK+raw-test-output/go-test-report.xml"


def test_retry_build(cci):
    get_mock(cci, "retry_build_response.json")
    resp = cci.retry_build("ccie-tester", "testing", "1")
    assert resp["reponame"] == "MOCK+testing"

    # with SSH
    resp = cci.retry_build("ccie-tester", "testing", "1", ssh=True)
    assert resp["reponame"] == "MOCK+testing"


def test_cancel_build(cci):
    get_mock(cci, "cancel_build_response.json")
    resp = cci.cancel_build("ccie-tester", "testing", "11")
    assert resp["reponame"] == "MOCK+testing"
    assert resp["build_num"] == 11
    assert resp["canceled"] is True


def test_add_ssh_user(cci):
    get_mock(cci, "add_ssh_user_response.json")
    resp = cci.add_ssh_user("ccie-tester", "testing", "11")
    assert resp["reponame"] == "MOCK+testing"
    assert resp["ssh_users"][0]["login"] == "ccie-tester"


def test_trigger_build(cci):
    get_mock(cci, "trigger_build_response.json")
    resp = cci.trigger_build("ccie-tester", "testing")
    assert resp["reponame"] == "MOCK+testing"


def test_trigger_pipeline(cci):
    get_mock(cci, "trigger_pipeline_response.json")
    resp = cci.trigger_pipeline("ccie-tester", "testing")
    assert resp["state"] == "pending"


def test_get_project_pipelines_depaginated(cci):
    get_mock(cci, "get_project_pipelines_response.json")
    resp = cci.get_project_pipelines("foo", "bar")
    assert resp[0]["project_slug"] == "gh/foo/bar"


def test_get_project_pipeline(cci):
    get_mock(cci, "get_project_pipeline_response.json")
    resp = cci.get_project_pipeline("foo", "bar", 1234)
    assert resp["number"] == 1234


def test_continue_pipeline(cci):
    get_mock(cci, "message_accepted_response.json")
    resp = cci.continue_pipeline("continuation_key", "config")
    assert_message_accepted(resp)


def test_get_pipelines(cci):
    get_mock(cci, "get_pipelines_response.json")
    resp = cci.get_pipelines("foo")
    assert resp[0]["project_slug"] == "gh/foo/bar"


def test_get_pipeline(cci):
    get_mock(cci, "get_pipeline_response.json")
    resp = cci.get_pipeline(TEST_ID)
    assert resp["state"] == "created"


def test_get_pipeline_config(cci):
    get_mock(cci, "get_pipeline_config_response.json")
    resp = cci.get_pipeline_config(TEST_ID)
    assert "source" in resp
    assert "compiled" in resp


def test_get_pipeline_workflow_depaginated(cci):
    get_mock(cci, "get_pipeline_workflow_response.json")
    resp = cci.get_pipeline_workflow(TEST_ID)
    assert resp[0]["project_slug"] == "gh/foo/bar"


def test_get_workflow(cci):
    get_mock(cci, "get_workflow_response.json")
    resp = cci.get_workflow(TEST_ID)
    assert resp["status"] == "running"


def test_get_workflow_jobs_depaginated(cci):
    get_mock(cci, "get_workflow_jobs_response.json")
    resp = cci.get_workflow_jobs(TEST_ID)
    assert len(resp) == 2


def test_approve_job(cci):
    get_mock(cci, "message_accepted_response.json")
    resp = cci.approve_job("workflow_id", "approval_request_id")
    assert_message_accepted(resp)


def test_list_checkout_keys(cci):
    get_mock(cci, "list_checkout_keys_response.json")
    resp = cci.list_checkout_keys("user", "circleci-sandbox")
    assert resp[0]["type"] == "deploy-key"
    assert "public_key" in resp[0]


def test_create_checkout_key(cci):
    with pytest.raises(CircleciError) as ex:
        cci.create_checkout_key("user", "test", "bad")
    assert "Invalid key type: bad" in str(ex.value)

    get_mock(cci, "create_checkout_key_response.json")
    resp = cci.create_checkout_key("user", "test", "deploy-key")
    assert resp["type"] == "deploy-key"
    assert "public_key" in resp


def test_get_checkout_key(cci):
    get_mock(cci, "get_checkout_key_response.json")
    resp = cci.get_checkout_key(
        "user",
        "circleci-sandbox",
        "94:19:ab:a9:f4:2b:21:1c:a5:87:dd:ee:3d:c2:90:4e",
    )
    assert resp["type"] == "deploy-key"
    assert "public_key" in resp


def test_delete_checkout_key(cci):
    get_mock(cci, "message_ok_response.json")
    resp = cci.delete_checkout_key(
        "user",
        "circleci-sandbox",
        "94:19:ab:a9:f4:2b:21:1c:a5:87:dd:ee:3d:c2:90:4e",
    )
    assert_message_ok(resp)


def test_get_test_metadata(cci):
    get_mock(cci, "get_test_metadata_response.json")
    resp = cci.get_test_metadata("user", "circleci-demo-javascript-express", 127)
    assert len(resp) == 2
    assert "tests" in resp


def test_list_envvars(cci):
    get_mock(cci, "list_envvars_response.json")
    resp = cci.list_envvars("user", "circleci-sandbox")
    assert len(resp) == 4
    assert resp[0]["name"] == "BAR"


def test_add_envvar(cci):
    get_mock(cci, "get_envvar_response.json")
    resp = cci.add_envvar("user", "circleci-sandbox", "foo", "bar")
    assert resp["name"] == "foo"
    assert resp["value"] != "bar"


def test_get_envvar(cci):
    get_mock(cci, "get_envvar_response.json")
    resp = cci.get_envvar("user", "circleci-sandbox", "foo")
    assert resp["name"] == "foo"
    assert resp["value"] != "bar"


def test_delete_envvar(cci):
    get_mock(cci, "message_ok_response.json")
    resp = cci.delete_envvar("user", "circleci-sandbox", "foo")
    assert_message_ok(resp)


def test_get_contexts_depaginated(cci):
    get_mock(cci, "get_contexts_response.json")
    resp = cci.get_contexts("user")
    cci._request_get_items.assert_called_once_with(
        "context",
        params={
            "owner-type": "organization",
            "owner-slug": "github/user",
        },
        paginate=False,
        limit=None,
    )
    assert resp[0]["id"] == TEST_ID
    assert resp[0]["name"] == "context1"
    assert resp[2]["name"] == "foobar"


def test_get_contexts_owner_id(cci):
    get_mock(cci, "get_contexts_response.json")
    resp = cci.get_contexts(owner_id=TEST_ID)
    cci._request_get_items.assert_called_once_with(
        "context",
        params={
            "owner-type": "organization",
            "owner-id": TEST_ID,
        },
        paginate=False,
        limit=None,
    )
    assert resp[0]["name"] == "context1"


def test_get_contexts_owner_type(cci):
    get_mock(cci, "get_contexts_response.json")
    resp = cci.get_contexts("user", owner_type="account")
    cci._request_get_items.assert_called_once_with(
        "context",
        params={
            "owner-type": "account",
            "owner-slug": "github/user",
        },
        paginate=False,
        limit=None,
    )
    assert resp[0]["name"] == "context1"


def test_add_context(cci):
    get_mock(cci, "get_context_response.json")
    resp = cci.add_context("testcontext", "user")
    cci._request.assert_called_once_with(
        POST,
        "context",
        data={
            "name": "testcontext",
            "owner": {
                "type": "organization",
                "slug": "github/user",
            },
        },
        api_version="v2",
    )
    assert resp["name"] == "testcontext"


def test_add_context_organization(cci):
    get_mock(cci, "get_context_response.json")
    resp = cci.add_context("testcontext", "user", owner_type="account")
    cci._request.assert_called_once_with(
        POST,
        "context",
        data={
            "name": "testcontext",
            "owner": {
                "type": "account",
                "slug": "github/user",
            },
        },
        api_version="v2",
    )
    assert resp["name"] == "testcontext"


def test_get_context(cci):
    get_mock(cci, "get_context_response.json")
    resp = cci.get_context(TEST_ID)
    cci._request.assert_called_once_with(
        GET,
        "context/{0}".format(TEST_ID),
        api_version="v2",
    )
    assert resp["name"] == "testcontext"


def test_delete_context(cci):
    get_mock(cci, "delete_context_response.json")
    resp = cci.delete_context(TEST_ID)
    cci._request.assert_called_once_with(
        DELETE,
        "context/{0}".format(TEST_ID),
        api_version="v2",
    )
    assert resp["message"] == "Context deleted."


def test_get_context_envvars_depaginated(cci):
    get_mock(cci, "get_context_envvars_response.json")
    resp = cci.get_context_envvars(TEST_ID)
    cci._request_get_items.assert_called_once_with(
        "context/{0}/environment-variable".format(TEST_ID),
        paginate=False,
        limit=None,
    )
    assert resp[1]["variable"] == "FOOBAR"
    assert resp[2]["variable"] == "FOOBAR2"


def test_add_context_envvar(cci):
    get_mock(cci, "add_context_envvar_response.json")
    resp = cci.add_context_envvar(TEST_ID, "FOOBAR", "BAZ")
    cci._request.assert_called_once_with(
        PUT,
        "context/{0}/environment-variable/FOOBAR".format(TEST_ID),
        api_version="v2",
        data={"value": "BAZ"},
    )
    assert resp["variable"] == "FOOBAR"


def test_delete_context_envvar(cci):
    get_mock(cci, "delete_context_envvar_response.json")
    resp = cci.delete_context_envvar(TEST_ID, "FOOBAR")
    cci._request.assert_called_once_with(
        DELETE,
        "context/{0}/environment-variable/FOOBAR".format(TEST_ID),
        api_version="v2",
    )
    assert resp["message"] == "Environment variable deleted."


def test_get_latest_artifact(cci):
    get_mock(cci, "get_latest_artifacts_response.json")
    resp = cci.get_latest_artifact("user", "circleci-sandbox")
    assert resp[0]["path"] == "circleci-docs/index.html"

    resp = cci.get_latest_artifact("user", "circleci-sandbox", "master")
    assert resp[0]["path"] == "circleci-docs/index.html"

    with pytest.raises(CircleciError) as ex:
        cci.get_latest_artifact("user", "circleci-sandbox", "master", "bad")
    assert "Invalid status: bad" in str(ex.value)


def test_get_project_settings(cci):
    get_mock(cci, "get_project_settings_response.json")
    resp = cci.get_project_settings("user", "circleci-sandbox")
    assert resp["default_branch"] == "master"


def test_get_project_branches(cci):
    get_mock(cci, "get_project_branches_response.json")
    resp = cci.get_project_branches("foo", "bar")
    assert "master" in resp["branches"]


def test_get_project_workflows_metrics_depaginated(cci):
    get_mock(cci, "get_project_workflows_metrics_response.json")
    resp = cci.get_project_workflows_metrics("foo", "bar")
    assert "metrics" in resp[0]
    assert "duration_metrics" in resp[0]["metrics"]


def test_get_project_workflow_metrics_depaginated(cci):
    get_mock(cci, "get_project_workflow_metrics_response.json")
    resp = cci.get_project_workflow_metrics("foo", "bar", "workflow")
    assert resp[0]["status"] == "success"
    assert "duration" in resp[0]


def test_get_project_workflow_test_metrics(cci):
    get_mock(cci, "get_project_workflow_test_metrics_response.json")
    resp = cci.get_project_workflow_test_metrics("foo", "bar", "workflow")
    assert resp["average_test_count"] == 2
    assert resp["total_test_runs"] == 3


def test_get_project_workflow_jobs_metrics_depaginated(cci):
    get_mock(cci, "get_project_workflow_jobs_metrics_response.json")
    resp = cci.get_project_workflow_jobs_metrics("foo", "bar", "workflow")
    assert "metrics" in resp[0]
    assert "duration_metrics" in resp[0]["metrics"]


def test_get_project_workflow_job_metrics_depaginated(cci):
    get_mock(cci, "get_project_workflow_job_metrics_response.json")
    resp = cci.get_project_workflow_job_metrics("foo", "bar", "workflow", "job")
    assert resp[0]["status"] == "success"
    assert "duration" in resp[0]


def test_get_schedules(cci):
    get_mock(cci, "get_schedules_response.json")
    resp = cci.get_schedules("foo", "bar")
    assert resp[0]["project-slug"] == "gh/foo/bar"
    assert resp[0]["name"] == "schedule1"


def test_get_schedule(cci):
    get_mock(cci, "get_schedule_response.json")
    resp = cci.get_schedule(TEST_ID)
    assert resp["project-slug"] == "gh/foo/bar"
    assert resp["name"] == "schedule1"


def test_add_schedule(cci):
    get_mock(cci, "get_schedule_response.json")
    data = {
        "name": "schedule1",
        "timetable": {"per-hour": 0, "hours-of-day": [0], "days-of-week": ["TUE"]},
        "attribution-actor": "current",
        "parameters": {"deploy_prod": True, "branch": "new_feature"},
    }
    resp = cci.add_schedule("foo", "bar", "schedule1", settings=data)
    assert resp["project-slug"] == "gh/foo/bar"
    assert resp["name"] == "schedule1"


def test_update_schedule(cci):
    get_mock(cci, "get_schedule_response.json")
    data = {"description": "test schedule"}
    resp = cci.update_schedule(TEST_ID, data)
    assert resp["description"] == "test schedule"


def test_delete_schedule(cci):
    get_mock(cci, "message_accepted_response.json")
    resp = cci.delete_schedule(TEST_ID)
    assert_message_accepted(resp)


def test_get_job_details(cci):
    get_mock(cci, "get_job_details_response.json")
    resp = cci.get_job_details("foo", "bar", 12345)
    assert resp["project"]["slug"] == "gh/foo/bar"
    assert resp["number"] == 12345


def test_cancel_job(cci):
    get_mock(cci, "message_accepted_response.json")
    resp = cci.cancel_job("foo", "bar", 12345)
    assert_message_accepted(resp)


def test_cancel_workflow(cci):
    get_mock(cci, "message_accepted_response.json")
    resp = cci.cancel_workflow(TEST_ID)
    assert_message_accepted(resp)


def test_rerun_workflow(cci):
    get_mock(cci, "message_accepted_response.json")
    resp = cci.rerun_workflow(TEST_ID, from_failed=True)
    assert_message_accepted(resp)
