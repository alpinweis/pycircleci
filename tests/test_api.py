import json
import pytest
from unittest.mock import MagicMock

from pycircleci.api import Api, CircleciError, DELETE, GET, POST, PUT


@pytest.fixture(scope="session")
def cci():
    """Initialize a CircleCI API client"""
    return Api("TOKEN")


def js(text):
    return json.loads(text)


def get_mock(api_client, filename):
    """Get a mock response from file"""
    filename = "tests/mocks/{0}".format(filename)
    with open(filename, "r") as f:
        resp = f.read()
        api_client._request = MagicMock(return_value=resp)
        api_client._request_get_depaginate = MagicMock(return_value=resp)


def test_bad_verb(cci):
    with pytest.raises(CircleciError) as ex:
        cci._request("BAD", "dummy")
    assert "Invalid verb: BAD" in str(ex.value)


def test_get_user_info(cci):
    get_mock(cci, "get_user_info_response")
    resp = js(cci.get_user_info())
    assert resp["selected_email"] == "mock+ccie-tester@circleci.com"


def test_get_project(cci):
    get_mock(cci, "get_project_response")
    resp = js(cci.get_project("gh/foo/bar"))
    assert resp["slug"] == "gh/foo/bar"
    assert resp["organization_name"] == "foo"
    assert resp["name"] == "bar"
    assert "vcs_info" in resp


def test_get_projects(cci):
    get_mock(cci, "get_projects_response")
    resp = js(cci.get_projects())
    assert resp[0]["vcs_url"] == "MOCK+https://ghe-dev.circleci.com/ccie-tester/testing"


def test_follow_project(cci):
    get_mock(cci, "follow_project_response")
    resp = js(cci.follow_project("ccie-tester", "testing"))
    assert resp["mock+following"] is True


def test_get_project_build_summary(cci):
    get_mock(cci, "get_project_build_summary_response")
    resp = js(cci.get_project_build_summary("ccie-tester", "testing"))
    assert resp[0]["username"] == "MOCK+ccie-tester"

    # with invalid status filter
    with pytest.raises(CircleciError) as ex:
        js(cci.get_project_build_summary("ccie-tester", "testing", status_filter="bad"))
    assert "Invalid status: bad" in str(ex.value)

    # with branch
    resp = js(cci.get_project_build_summary("ccie-tester", "testing", branch="master"))
    assert resp[0]["username"] == "MOCK+ccie-tester"


def test_get_recent_builds(cci):
    get_mock(cci, "get_recent_builds_response")
    resp = js(cci.get_recent_builds())
    assert resp[0]["reponame"] == "MOCK+testing"


def test_get_build_info(cci):
    get_mock(cci, "get_build_info_response")
    resp = js(cci.get_build_info("ccie-tester", "testing", "1"))
    assert resp["reponame"] == "MOCK+testing"


def test_get_artifacts(cci):
    get_mock(cci, "get_artifacts_response")
    resp = js(cci.get_artifacts("ccie-tester", "testing", "1"))
    assert resp[0]["path"] == "MOCK+raw-test-output/go-test-report.xml"


def test_retry_build(cci):
    get_mock(cci, "retry_build_response")
    resp = js(cci.retry_build("ccie-tester", "testing", "1"))
    assert resp["reponame"] == "MOCK+testing"

    # with SSH
    resp = js(cci.retry_build("ccie-tester", "testing", "1", ssh=True))
    assert resp["reponame"] == "MOCK+testing"


def test_cancel_build(cci):
    get_mock(cci, "cancel_build_response")
    resp = js(cci.cancel_build("ccie-tester", "testing", "11"))
    assert resp["reponame"] == "MOCK+testing"
    assert resp["build_num"] == 11
    assert resp["canceled"] is True


def test_add_ssh_user(cci):
    get_mock(cci, "add_ssh_user_response")
    resp = js(cci.add_ssh_user("ccie-tester", "testing", "11"))
    assert resp["reponame"] == "MOCK+testing"
    assert resp["ssh_users"][0]["login"] == "ccie-tester"


def test_trigger_build(cci):
    get_mock(cci, "trigger_build_response")
    resp = js(cci.trigger_build("ccie-tester", "testing"))
    assert resp["reponame"] == "MOCK+testing"


def test_trigger_pipeline(cci):
    get_mock(cci, "trigger_pipeline_response")
    resp = js(cci.trigger_pipeline("ccie-tester", "testing"))
    assert resp["state"] == "pending"


def test_get_project_pipelines_depaginated(cci):
    get_mock(cci, "get_project_pipelines_response")
    resp = js(cci.get_project_pipelines("foo", "bar"))
    assert resp[0]["project_slug"] == "gh/foo/bar"


def test_get_project_pipeline(cci):
    get_mock(cci, "get_project_pipeline_response")
    resp = js(cci.get_project_pipeline("foo", "bar", 1234))
    assert resp["number"] == 1234


def test_get_pipeline(cci):
    get_mock(cci, "get_pipeline_response")
    resp = js(cci.get_pipeline("dummy-pipeline-id"))
    assert resp["state"] == "created"


def test_get_pipeline_config(cci):
    get_mock(cci, "get_pipeline_config_response")
    resp = js(cci.get_pipeline_config("dummy-pipeline-id"))
    assert "source" in resp
    assert "compiled" in resp


def test_get_pipeline_workflow_depaginated(cci):
    get_mock(cci, "get_pipeline_workflow_response")
    resp = js(cci.get_pipeline_workflow("dummy-pipeline-id"))
    assert resp[0]["project_slug"] == "gh/foo/bar"


def test_get_workflow(cci):
    get_mock(cci, "get_workflow_response")
    resp = js(cci.get_workflow("dummy-workflow-id"))
    assert resp["status"] == "running"


def test_get_workflow_jobs_depaginated(cci):
    get_mock(cci, "get_workflow_jobs_response")
    resp = js(cci.get_workflow_jobs("dummy-workflow-id"))
    assert len(resp) == 2


def test_approve_job(cci):
    get_mock(cci, "approve_job_response")
    resp = js(cci.approve_job("workflow_id", "approval_request_id"))
    assert resp["message"] == "Accepted."


def test_list_checkout_keys(cci):
    get_mock(cci, "list_checkout_keys_response")
    resp = js(cci.list_checkout_keys("user", "circleci-sandbox"))
    assert resp[0]["type"] == "deploy-key"
    assert "public_key" in resp[0]


def test_create_checkout_key(cci):
    with pytest.raises(CircleciError) as ex:
        cci.create_checkout_key("user", "test", "bad")
    assert "Invalid key type: bad" in str(ex.value)

    get_mock(cci, "create_checkout_key_response")
    resp = js(cci.create_checkout_key("user", "test", "deploy-key"))
    assert resp["type"] == "deploy-key"
    assert "public_key" in resp


def test_get_checkout_key(cci):
    get_mock(cci, "get_checkout_key_response")
    resp = js(
        cci.get_checkout_key(
            "user",
            "circleci-sandbox",
            "94:19:ab:a9:f4:2b:21:1c:a5:87:dd:ee:3d:c2:90:4e",
        )
    )
    assert resp["type"] == "deploy-key"
    assert "public_key" in resp


def test_delete_checkout_key(cci):
    get_mock(cci, "delete_checkout_key_response")
    resp = js(
        cci.delete_checkout_key(
            "user",
            "circleci-sandbox",
            "94:19:ab:a9:f4:2b:21:1c:a5:87:dd:ee:3d:c2:90:4e",
        )
    )
    assert resp["message"] == "ok"


def test_get_test_metadata(cci):
    get_mock(cci, "get_test_metadata_response")
    resp = js(cci.get_test_metadata("user", "circleci-demo-javascript-express", 127))
    assert len(resp) == 2
    assert "tests" in resp


def test_list_envvars(cci):
    get_mock(cci, "list_envvars_response")
    resp = js(cci.list_envvars("user", "circleci-sandbox"))
    assert len(resp) == 4
    assert resp[0]["name"] == "BAR"


def test_add_envvar(cci):
    get_mock(cci, "add_envvar_response")
    resp = js(cci.add_envvar("user", "circleci-sandbox", "foo", "bar"))
    assert resp["name"] == "foo"
    assert resp["value"] != "bar"


def test_get_envvar(cci):
    get_mock(cci, "get_envvar_response")
    resp = js(cci.get_envvar("user", "circleci-sandbox", "foo"))
    assert resp["name"] == "foo"
    assert resp["value"] != "bar"


def test_delete_envvar(cci):
    get_mock(cci, "delete_envvar_response")
    resp = js(cci.delete_envvar("user", "circleci-sandbox", "foo"))
    assert resp["message"] == "ok"


def test_get_contexts_depaginated(cci):
    get_mock(cci, "get_contexts_response")
    resp = js(cci.get_contexts("user"))

    cci._request_get_depaginate.assert_called_once_with(
        "context",
        params={
            "owner-type": "organization",
            "owner-slug": "github/user",
        },
        api_version="v2",
        paginate=False,
        limit=None,
    )
    assert resp[0]["id"] == "a2683f02-d716-4b1e-bb61-d8a5cf5308f1"
    assert resp[0]["name"] == "context1"
    assert resp[2]["name"] == "foobar"


def test_get_contexts_owner_id(cci):
    get_mock(cci, "get_contexts_response")
    resp = js(cci.get_contexts(owner_id="c65b68ef-e73b-4bf2-be9a-7a322a9df150"))

    cci._request_get_depaginate.assert_called_once_with(
        "context",
        params={
            "owner-type": "organization",
            "owner-id": "c65b68ef-e73b-4bf2-be9a-7a322a9df150",
        },
        api_version="v2",
        paginate=False,
        limit=None,
    )
    assert resp[0]["name"] == "context1"


def test_get_contexts_owner_type(cci):
    get_mock(cci, "get_contexts_response")
    resp = js(cci.get_contexts("user", owner_type="account"))

    cci._request_get_depaginate.assert_called_once_with(
        "context",
        params={
            "owner-type": "account",
            "owner-slug": "github/user",
        },
        api_version="v2",
        paginate=False,
        limit=None,
    )
    assert resp[0]["name"] == "context1"


def test_add_context(cci):
    get_mock(cci, "add_context_response")
    resp = js(cci.add_context("testcontext", "user"))

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
    get_mock(cci, "add_context_response")
    resp = js(cci.add_context("testcontext", "user", owner_type="account"))

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
    get_mock(cci, "get_context_response")
    resp = js(cci.get_context("497f6eca-6276-4993-bfeb-53cbbbba6f08"))

    cci._request.assert_called_once_with(
        GET,
        "context/497f6eca-6276-4993-bfeb-53cbbbba6f08",
        api_version="v2",
    )
    assert resp["name"] == "testcontext"


def test_delete_context(cci):
    get_mock(cci, "delete_context_response")
    resp = js(cci.delete_context("497f6eca-6276-4993-bfeb-53cbbbba6f08"))

    cci._request.assert_called_once_with(
        DELETE,
        "context/497f6eca-6276-4993-bfeb-53cbbbba6f08",
        api_version="v2",
    )
    assert resp["message"] == "Context deleted."


def test_get_context_envvars_depaginated(cci):
    get_mock(cci, "get_context_envvars_response")
    resp = js(cci.get_context_envvars("a5b6416b-369e-44a9-8d47-8970325d4134"))

    cci._request_get_depaginate.assert_called_once_with(
        "context/a5b6416b-369e-44a9-8d47-8970325d4134/environment-variable",
        api_version="v2",
        paginate=False,
        limit=None,
    )
    assert resp[1]["variable"] == "FOOBAR"
    assert resp[2]["variable"] == "FOOBAR2"


def test_add_context_envvar(cci):
    get_mock(cci, "add_context_envvar_response")
    resp = js(
        cci.add_context_envvar("f31d7249-b7b1-4729-b3a4-ec0ba07b4686", "FOOBAR", "BAZ")
    )

    cci._request.assert_called_once_with(
        PUT,
        "context/f31d7249-b7b1-4729-b3a4-ec0ba07b4686/environment-variable/FOOBAR",
        api_version="v2",
        data={"value": "BAZ"},
    )
    assert resp["variable"] == "FOOBAR"


def test_delete_context_envvar(cci):
    get_mock(cci, "delete_context_envvar_response")
    resp = js(
        cci.delete_context_envvar("f31d7249-b7b1-4729-b3a4-ec0ba07b4686", "FOOBAR")
    )

    cci._request.assert_called_once_with(
        DELETE,
        "context/f31d7249-b7b1-4729-b3a4-ec0ba07b4686/environment-variable/FOOBAR",
        api_version="v2",
    )
    assert resp["message"] == "Environment variable deleted."


def test_get_latest_artifact(cci):
    get_mock(cci, "get_latest_artifacts_response")
    resp = js(cci.get_latest_artifact("user", "circleci-sandbox"))
    assert resp[0]["path"] == "circleci-docs/index.html"

    resp = js(cci.get_latest_artifact("user", "circleci-sandbox", "master"))
    assert resp[0]["path"] == "circleci-docs/index.html"

    with pytest.raises(CircleciError) as ex:
        cci.get_latest_artifact("user", "circleci-sandbox", "master", "bad")
    assert "Invalid status: bad" in str(ex.value)


def test_get_project_settings(cci):
    get_mock(cci, "get_project_settings_response")
    resp = js(cci.get_project_settings("user", "circleci-sandbox"))
    assert resp["default_branch"] == "master"


def test_get_project_workflows_metrics_depaginated(cci):
    get_mock(cci, "get_project_workflows_metrics_response")
    resp = js(cci.get_project_workflows_metrics("foo", "bar"))
    assert "metrics" in resp[0]
    assert "duration_metrics" in resp[0]["metrics"]


def test_get_project_workflow_metrics_depaginated(cci):
    get_mock(cci, "get_project_workflow_metrics_response")
    resp = js(cci.get_project_workflow_metrics("foo", "bar", "workflow"))
    assert resp[0]["status"] == "success"
    assert "duration" in resp[0]


def test_get_project_workflow_jobs_metrics_depaginated(cci):
    get_mock(cci, "get_project_workflow_jobs_metrics_response")
    resp = js(cci.get_project_workflow_jobs_metrics("foo", "bar", "workflow"))
    assert "metrics" in resp[0]
    assert "duration_metrics" in resp[0]["metrics"]


def test_get_project_workflow_job_metrics_depaginated(cci):
    get_mock(cci, "get_project_workflow_job_metrics_response")
    resp = js(cci.get_project_workflow_job_metrics("foo", "bar", "workflow", "job"))
    assert resp[0]["status"] == "success"
    assert "duration" in resp[0]


def test_get_job_details(cci):
    get_mock(cci, "get_job_details_response")
    resp = js(cci.get_job_details("foo", "bar", 12345))
    assert resp["project"]["slug"] == "gh/foo/bar"
    assert resp["number"] == 12345
