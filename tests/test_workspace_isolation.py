from fastapi.testclient import TestClient

from syntra.main import app


def _sign_up(client: TestClient, email: str, workspace_name: str) -> None:
    response = client.post(
        "/auth/sign-up",
        data={
            "email": email,
            "name": email.split("@")[0],
            "password": "secret-password",
            "workspace_name": workspace_name,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def _register_project(client: TestClient, name: str, repo: str) -> None:
    response = client.post(
        "/app/projects",
        data={"name": name, "repository_url": repo, "default_branch": "main"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def _create_bug(client: TestClient, project_name: str, title: str) -> None:
    response = client.post(
        "/app/bugs",
        data={
            "project_name": project_name,
            "title": title,
            "description": f"{title} description",
            "priority": "low",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_workspace_pages_do_not_show_other_workspace_records():
    first = TestClient(app)
    second = TestClient(app)

    _sign_up(first, "first@example.com", "First Workspace")
    _sign_up(second, "second@example.com", "Second Workspace")

    _register_project(first, "crm-web", "https://github.com/example/first")
    _register_project(second, "crm-web", "https://github.com/example/second")
    _create_bug(first, "crm-web", "First private bug")

    first_projects = first.get("/app/projects").text
    second_projects = second.get("/app/projects").text
    second_bugs = second.get("/app/bugs").text

    assert "https://github.com/example/first" in first_projects
    assert "https://github.com/example/first" not in second_projects
    assert "https://github.com/example/second" in second_projects
    assert "First private bug" not in second_bugs


def test_public_project_registration_is_disabled():
    client = TestClient(app)
    response = client.post(
        "/projects",
        json={
            "name": "global-project",
            "repository_url": "https://github.com/example/global",
            "default_branch": "main",
        },
    )

    assert response.status_code == 410
