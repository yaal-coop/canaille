import os


def create_mo_files(setup_kwargs):
    from babel.messages.frontend import compile_catalog

    cmd = compile_catalog()
    cmd.directory = os.path.join(os.path.dirname(__file__), "canaille", "translations")
    cmd.quiet = True
    cmd.statistics = True
    cmd.finalize_options()
    cmd.run()
    return setup_kwargs


if __name__ == "__main__":
    create_mo_files({})
