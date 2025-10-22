def test_version(testclient):
    """Test that the about page is accessible."""
    testclient.get("/about", status=200)


def test_javascript(testclient):
    """Test that JavaScript is included or excluded based on configuration."""
    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    res = testclient.get("/about", status=200)
    res.mustcontain("</script>")

    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = False
    res = testclient.get("/about", status=200)
    res.mustcontain(no="</script>")


def test_htmx(testclient):
    """Test that HTMX is included or excluded based on configuration."""
    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["CANAILLE"]["HTMX"] = True
    res = testclient.get("/about", status=200)
    res.mustcontain("htmx.min.js")
    res.mustcontain("hx-boost")

    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["CANAILLE"]["HTMX"] = False
    res = testclient.get("/about", status=200)
    res.mustcontain(no="htmx.min.js")
    res.mustcontain(no="hx-boost")
