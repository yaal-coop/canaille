import os
import pathlib
import sys
from urllib.parse import urlparse
from wsgiref.simple_server import WSGIRequestHandler

import tomlkit

sys.path.insert(0, os.path.abspath(".."))
from dev.devapp import create_app

WSGIRequestHandler.log_request = lambda *args, **kwargs: None


def create_doc_app(sphinx_app):
    conf_path = pathlib.Path(__file__).parent.parent / "dev" / "conf" / "canaille.toml"
    with open(conf_path) as fd:
        conf = dict(tomlkit.load(fd))
    conf["CANAILLE"]["DATABASE"] = "memory"
    conf["CANAILLE"]["SECRET_KEY"] = "doc"
    conf["CANAILLE"]["SMTP"] = {"HOST": "localhost"}
    conf["CANAILLE"]["LANGUAGE"] = sphinx_app.config["language"]
    app = create_app(conf)
    return app


def get_root_url(url):
    parsed_url = urlparse(url)
    root_url = f"{parsed_url.scheme}://{parsed_url.hostname}"
    if parsed_url.port:
        root_url += f":{parsed_url.port}"
    return root_url


contexts = {}


def context_login(browser, url, color_scheme, user, password=True):
    try:
        context = browser.new_context(
            color_scheme=color_scheme, storage_state=contexts[user]
        )
    except KeyError:
        context = browser.new_context(color_scheme=color_scheme)

        page = context.new_page()
        page.goto(get_root_url(url) + "/login")
        page.wait_for_load_state()
        page.locator("input[name=login]").fill(user)
        page.click("*[type=submit]")
        page.wait_for_load_state()

        if password:
            page.locator("input[name=password]").fill(user)
            page.locator("*[type=submit]").click()
            page.wait_for_load_state()

        contexts[user] = context.storage_state()
    return context


def admin_login(browser, url, color_scheme):
    return context_login(browser, url, color_scheme, "admin")


def user_login(browser, url, color_scheme):
    return context_login(browser, url, color_scheme, "user")


def james_login(browser, url, color_scheme):
    return context_login(browser, url, color_scheme, "james", password=False)
