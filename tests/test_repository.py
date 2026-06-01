from syntra.services.repository import RepositoryService


def test_repository_detects_node_project_and_candidate_file(tmp_path):
    (tmp_path / "package.json").write_text('{"scripts":{"test":"echo ok"}}', encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "login.ts").write_text("function loginButton() {}", encoding="utf-8")

    result = RepositoryService().analyze(tmp_path, "login button broken")

    assert "node" in result["runtimes"]
    assert "src/login.ts" in result["candidate_files"]
