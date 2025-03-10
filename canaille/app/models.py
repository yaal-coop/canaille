from canaille.core.models import Model

MODELS: dict[str, type[Model]] = {}


def __getattr__(name):
    if name.lower() in MODELS:
        return MODELS[name.lower()]


def register(model):
    MODELS[model.__name__.lower()] = model
