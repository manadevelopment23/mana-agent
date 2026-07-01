from pathlib import Path

from typer.testing import CliRunner

from mana_agent.commands.cli import app

runner = CliRunner()


def test_plan_mode_loads_matching_skills_and_saves(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "plan",
            "--repo",
            str(tmp_path),
            "--no-code",
            "Add CLI smoke test",
        ],
    )

    assert result.exit_code == 0
    assert "Loaded skills: cli, testing" in result.output
    assert "# Implementation Plan" in result.output
    assert (tmp_path / ".mana" / "plans" / "add-cli-smoke-test.md").exists()


def test_skills_init_list_show_uses_root_directory(tmp_path: Path) -> None:
    result_init = runner.invoke(app, ["skills", "init", "--repo", str(tmp_path)])
    assert result_init.exit_code == 0
    assert (tmp_path / "skills" / "cli.md").exists()

    custom = "# CLI Skill\n\ncustom root skill\n"
    (tmp_path / "skills" / "cli.md").write_text(custom, encoding="utf-8")
    result_init_again = runner.invoke(app, ["skills", "init", "--repo", str(tmp_path)])
    assert result_init_again.exit_code == 0
    assert (tmp_path / "skills" / "cli.md").read_text(encoding="utf-8") == custom

    result_list = runner.invoke(app, ["skills", "list", "--repo", str(tmp_path)])
    assert result_list.exit_code == 0
    assert "Project Root Skills" in result_list.output
    assert "- cli" in result_list.output

    result_show = runner.invoke(app, ["skills", "show", "cli", "--repo", str(tmp_path)])
    assert result_show.exit_code == 0
    assert "custom root skill" in result_show.output


def test_root_flag_dispatches_plan_mode(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["--plan", "--repo", str(tmp_path)],
        input="Add CLI banner\n",
    )

    assert result.exit_code == 0
    assert "Plan Mode" in result.output
    assert "Loaded skills: cli" in result.output
