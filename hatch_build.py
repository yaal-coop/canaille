import os

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def create_mo_files():
    from babel.messages.frontend import compile_catalog

    cmd = compile_catalog()
    cmd.directory = os.path.join(os.path.dirname(__file__), "canaille", "translations")
    cmd.quiet = True
    cmd.statistics = True
    cmd.finalize_options()
    cmd.run()


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        create_mo_files()


if __name__ == "__main__":
    create_mo_files({})
