def test_favicon(testclient):
    """The favicon is displayed."""
    testclient.app.config["CANAILLE"]["FAVICON"] = "/static/img/favicon.webp"

    res = testclient.get("/login")
    assert res.pyquery("link[rel=icon]").attr("href") == "/static/img/favicon.webp"


def test_favicon_without_logo(testclient):
    """The favicon is displayed when no logo is configured."""
    testclient.app.config["CANAILLE"]["LOGO"] = None
    testclient.app.config["CANAILLE"]["FAVICON"] = "/static/img/favicon.webp"

    res = testclient.get("/login")
    assert res.pyquery("link[rel=icon]").attr("href") == "/static/img/favicon.webp"


def test_favicon_defaults_to_logo(testclient):
    """The logo is used as favicon when no favicon is configured."""
    testclient.app.config["CANAILLE"]["LOGO"] = "/static/img/logo.webp"
    testclient.app.config["CANAILLE"]["FAVICON"] = None

    res = testclient.get("/login")
    assert res.pyquery("link[rel=icon]").attr("href") == "/static/img/logo.webp"


def test_no_favicon(testclient):
    """No favicon is displayed when neither a favicon nor a logo is configured."""
    testclient.app.config["CANAILLE"]["LOGO"] = None
    testclient.app.config["CANAILLE"]["FAVICON"] = None

    res = testclient.get("/login")
    assert not res.pyquery("link[rel=icon]")
