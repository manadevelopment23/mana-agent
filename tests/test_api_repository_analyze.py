from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from mana_agent.api.app import create_app
from mana_agent.api.services.job_service import ApiJobStore
from mana_agent.services.execution_event_hub import reset_execution_event_hub_for_tests


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, Path]:
    monkeypatch.setenv("MANA_HOME", str(tmp_path / "mana_home"))
    monkeypatch.delenv("MANA_API_TOKEN", raising=False)
    reset_execution_event_hub_for_tests()
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("# demo\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    monkeypatch.setenv("MANA_DASHBOARD_ROOT", str(root))
    return TestClient(create_app()), root


def test_start_analyze_job_and_failure_path(client: tuple[TestClient, Path]) -> None:
    api, root = client
    from mana_agent.workspaces.paths import repository_id_for_path

    repo_id = repository_id_for_path(root)

    class Boom:
        def run(self, *args, **kwargs):  # noqa: ANN001
            raise RuntimeError("analyze exploded")

    with patch("mana_agent.services.project_analyze_service.ProjectAnalyzeService", Boom):
        response = api.post(
            f"/api/v1/repositories/{repo_id}/analyze",
            json={"depth": "quick", "with_llm": False, "root": str(root)},
        )
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        # BackgroundTasks run eagerly in TestClient
        job = ApiJobStore().get(job_id)
        assert job["status"] == "failed"
        assert "analyze exploded" in job.get("error", "")


def test_analysis_missing_is_reported(client: tuple[TestClient, Path]) -> None:
    api, root = client
    from mana_agent.workspaces.paths import repository_id_for_path

    repo_id = repository_id_for_path(root)
    response = api.get(f"/api/v1/repositories/{repo_id}/analysis", params={"root": str(root)})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["status"] in {"missing", "ready"}
