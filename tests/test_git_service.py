from syntra.services.git_service import slugify


def test_slugify_keeps_branch_titles_short_and_safe():
    assert slugify("Login Button: broken!") == "login-button-broken"
