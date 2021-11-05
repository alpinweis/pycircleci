import json
import unittest
from unittest.mock import MagicMock

from pycircleci.api import Api, CircleciError


def js(text):
    return json.loads(text)


class TestCircleciApi(unittest.TestCase):
    def setUp(self):
        self.c = Api("token")

    def get_mock(self, filename):
        """Get a mock response from file"""
        filename = "tests/mocks/{0}".format(filename)
        with open(filename, "r") as f:
            self.c._request = self.c._request_get_depaginate = MagicMock(return_value=f.read())

    def test_bad_verb(self):
        with self.assertRaises(CircleciError) as e:
            self.c._request("BAD", "dummy")

        self.assertIn("Invalid verb: BAD", str(e.exception))

    def test_get_user_info(self):
        self.get_mock("user_info_response")
        resp = js(self.c.get_user_info())

        self.assertEqual(resp["selected_email"], "mock+ccie-tester@circleci.com")

    def test_get_project(self):
        self.get_mock("get_project_response")
        resp = js(self.c.get_project("gh/foo/bar"))

        self.assertEqual(resp["slug"], "gh/foo/bar")
        self.assertEqual(resp["organization_name"], "foo")
        self.assertEqual(resp["name"], "bar")
        self.assertIn("vcs_info", resp)

    def test_get_projects(self):
        self.get_mock("get_projects_response")
        resp = js(self.c.get_projects())

        self.assertEqual(resp[0]["vcs_url"], "MOCK+https://ghe-dev.circleci.com/ccie-tester/testing")

    def test_follow_project(self):
        self.get_mock("follow_project_response")
        resp = js(self.c.follow_project("ccie-tester", "testing"))

        self.assertEqual(resp["mock+following"], True)

    def test_get_project_build_summary(self):
        self.get_mock("project_build_summary_response")
        resp = js(self.c.get_project_build_summary("ccie-tester", "testing"))

        self.assertEqual(len(resp), 6)
        self.assertEqual(resp[0]["username"], "MOCK+ccie-tester")

        # with invalid status filter
        with self.assertRaises(CircleciError) as e:
            js(self.c.get_project_build_summary("ccie-tester", "testing", status_filter="bad"))

        self.assertIn("Invalid status: bad", str(e.exception))

        # with branch
        resp = js(self.c.get_project_build_summary("ccie-tester", "testing", branch="master"))

        self.assertEqual(len(resp), 6)
        self.assertEqual(resp[0]["username"], "MOCK+ccie-tester")

    def test_get_recent_builds(self):
        self.get_mock("get_recent_builds_response")
        resp = js(self.c.get_recent_builds())

        self.assertEqual(len(resp), 7)
        self.assertEqual(resp[0]["reponame"], "MOCK+testing")

    def test_get_build_info(self):
        self.get_mock("get_build_info_response")
        resp = js(self.c.get_build_info("ccie-tester", "testing", "1"))

        self.assertEqual(resp["reponame"], "MOCK+testing")

    def test_get_artifacts(self):
        self.get_mock("get_artifacts_response")
        resp = js(self.c.get_artifacts("ccie-tester", "testing", "1"))

        self.assertEqual(resp[0]["path"], "MOCK+raw-test-output/go-test-report.xml")

    def test_retry_build(self):
        self.get_mock("retry_build_response")
        resp = js(self.c.retry_build("ccie-tester", "testing", "1"))

        self.assertEqual(resp["reponame"], "MOCK+testing")

        # with SSH
        resp = js(self.c.retry_build("ccie-tester", "testing", "1", ssh=True))

        self.assertEqual(resp["reponame"], "MOCK+testing")

    def test_cancel_build(self):
        self.get_mock("cancel_build_response")
        resp = js(self.c.cancel_build("ccie-tester", "testing", "11"))

        self.assertEqual(resp["reponame"], "MOCK+testing")
        self.assertEqual(resp["build_num"], 11)
        self.assertTrue(resp["canceled"])

    def test_add_ssh_user(self):
        self.get_mock("add_ssh_user_response")
        resp = js(self.c.add_ssh_user("ccie-tester", "testing", "11"))

        self.assertEqual(resp["reponame"], "MOCK+testing")
        self.assertEqual(resp["ssh_users"][0]["login"], "ccie-tester")

    def test_trigger_build(self):
        self.get_mock("trigger_build_response")
        resp = js(self.c.trigger_build("ccie-tester", "testing"))

        self.assertEqual(resp["reponame"], "MOCK+testing")

    def test_trigger_pipeline(self):
        self.get_mock("trigger_pipeline_response")
        resp = js(self.c.trigger_pipeline("ccie-tester", "testing"))

        self.assertEqual(resp["state"], "pending")

    def test_get_project_pipelines(self):
        self.get_mock("get_project_pipelines_response")
        resp = js(self.c.get_project_pipelines("foo", "bar"))

        self.assertEqual(resp["items"][0]["project_slug"], "gh/foo/bar")

    def test_get_project_pipeline(self):
        self.get_mock("get_project_pipeline_response")
        resp = js(self.c.get_project_pipeline("foo", "bar", 1234))

        self.assertEqual(resp["number"], 1234)

    def test_get_pipeline(self):
        self.get_mock("get_pipeline_response")
        resp = js(self.c.get_pipeline("dummy-pipeline-id"))

        self.assertEqual(resp["state"], "created")

    def test_get_pipeline_config(self):
        self.get_mock("get_pipeline_config_response")
        resp = js(self.c.get_pipeline_config("dummy-pipeline-id"))

        self.assertIn("source", resp)
        self.assertIn("compiled", resp)

    def test_get_pipeline_workflow(self):
        self.get_mock("get_pipeline_workflow_response")
        resp = js(self.c.get_pipeline_workflow("dummy-pipeline-id"))

        self.assertEqual(resp["items"][0]["project_slug"], "gh/foo/bar")

    def test_get_workflow(self):
        self.get_mock("get_workflow_response")
        resp = js(self.c.get_workflow("dummy-workflow-id"))

        self.assertEqual(resp["status"], "running")

    def test_get_workflow_jobs(self):
        self.get_mock("get_workflow_jobs_response")
        resp = js(self.c.get_workflow_jobs("dummy-workflow-id"))

        self.assertEqual(len(resp["items"]), 2)

    def test_approve_job(self):
        self.get_mock("approve_job_response")
        resp = js(self.c.approve_job("workflow_id", "approval_request_id"))

        self.assertEqual(resp["message"], "Accepted.")

    def test_list_checkout_keys(self):
        self.get_mock("list_checkout_keys_response")
        resp = js(self.c.list_checkout_keys("user", "circleci-sandbox"))

        self.assertEqual(resp[0]["type"], "deploy-key")
        self.assertIn("public_key", resp[0])

    def test_create_checkout_key(self):
        with self.assertRaises(CircleciError) as e:
            self.c.create_checkout_key("user", "test", "bad")

        self.assertIn("Invalid key type: bad", str(e.exception))

        self.get_mock("create_checkout_key_response")
        resp = js(self.c.create_checkout_key("user", "test", "deploy-key"))

        self.assertEqual(resp["type"], "deploy-key")
        self.assertIn("public_key", resp)

    def test_get_checkout_key(self):
        self.get_mock("get_checkout_key_response")
        resp = js(self.c.get_checkout_key("user", "circleci-sandbox", "94:19:ab:a9:f4:2b:21:1c:a5:87:dd:ee:3d:c2:90:4e"))

        self.assertEqual(resp["type"], "deploy-key")
        self.assertIn("public_key", resp)

    def test_delete_checkout_key(self):
        self.get_mock("delete_checkout_key_response")
        resp = js(self.c.delete_checkout_key("user", "circleci-sandbox", "94:19:ab:a9:f4:2b:21:1c:a5:87:dd:ee:3d:c2:90:4e"))

        self.assertEqual(resp["message"], "ok")

    def test_get_test_metadata(self):
        self.get_mock("get_test_metadata_response")
        resp = js(self.c.get_test_metadata("user", "circleci-demo-javascript-express", 127))

        self.assertEqual(len(resp), 2)
        self.assertIn("tests", resp)

    def test_list_envvars(self):
        self.get_mock("list_envvars_response")
        resp = js(self.c.list_envvars("user", "circleci-sandbox"))

        self.assertEqual(len(resp), 4)
        self.assertEqual(resp[0]["name"], "BAR")

    def test_add_envvar(self):
        self.get_mock("add_envvar_response")
        resp = js(self.c.add_envvar("user", "circleci-sandbox", "foo", "bar"))

        self.assertEqual(resp["name"], "foo")
        self.assertNotEqual(resp["value"], "bar")

    def test_get_envvar(self):
        self.get_mock("get_envvar_response")
        resp = js(self.c.get_envvar("user", "circleci-sandbox", "foo"))

        self.assertEqual(resp["name"], "foo")
        self.assertNotEqual(resp["value"], "bar")

    def test_delete_envvar(self):
        self.get_mock("delete_envvar_response")
        resp = js(self.c.delete_envvar("user", "circleci-sandbox", "foo"))

        self.assertEqual(resp["message"], "ok")

    def test_get_latest_artifact(self):
        self.get_mock("get_latest_artifacts_response")
        resp = js(self.c.get_latest_artifact("user", "circleci-sandbox"))

        self.assertEqual(resp[0]["path"], "circleci-docs/index.html")

        resp = js(self.c.get_latest_artifact("user", "circleci-sandbox", "master"))
        self.assertEqual(resp[0]["path"], "circleci-docs/index.html")

        with self.assertRaises(CircleciError) as e:
            self.c.get_latest_artifact("user", "circleci-sandbox", "master", "bad")

        self.assertIn("Invalid status: bad", str(e.exception))

    def test_get_project_settings(self):
        self.get_mock("get_project_settings_response")
        resp = js(self.c.get_project_settings("user", "circleci-sandbox"))

        self.assertEqual(resp["default_branch"], "master")

    def test_get_project_workflows_metrics(self):
        self.get_mock("get_project_workflows_metrics_response")
        resp = js(self.c.get_project_workflows_metrics("foo", "bar"))

        self.assertIn("metrics", resp["items"][0])
        self.assertIn("duration_metrics", resp["items"][0]["metrics"])

    def test_get_project_workflow_metrics(self):
        self.get_mock("get_project_workflow_metrics_response")
        resp = js(self.c.get_project_workflow_metrics("foo", "bar", "workflow"))

        self.assertEqual(resp["items"][0]["status"], "success")
        self.assertIn("duration", resp["items"][0])

    def test_get_project_workflow_jobs_metrics(self):
        self.get_mock("get_project_workflow_jobs_metrics_response")
        resp = js(self.c.get_project_workflow_jobs_metrics("foo", "bar", "workflow"))

        self.assertIn("metrics", resp["items"][0])
        self.assertIn("duration_metrics", resp["items"][0]["metrics"])

    def test_get_project_workflow_job_metrics(self):
        self.get_mock("get_project_workflow_job_metrics_response")
        resp = js(self.c.get_project_workflow_job_metrics("foo", "bar", "workflow", "job"))

        self.assertEqual(resp["items"][0]["status"], "success")
        self.assertIn("duration", resp["items"][0])

    def test_get_job_details(self):
        self.get_mock("get_job_details_response")
        resp = js(self.c.get_job_details("foo", "bar", 12345))

        self.assertEqual(resp["project"]["slug"], "gh/foo/bar")
        self.assertEqual(resp["number"], 12345)
