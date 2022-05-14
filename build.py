import subprocess


def create_mo_files(setup_kwargs):
    print("Compile translations:")
    subprocess.run(["pybabel", "compile", "--directory", "canaille/translations"])
    return setup_kwargs


if __name__ == "__main__":
    create_mo_files({})
