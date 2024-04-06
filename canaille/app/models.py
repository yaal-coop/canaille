MODELS = {}


def __getattr__(name):
    if name.lower() in MODELS:
        return MODELS[name.lower()]


def register(model):
    MODELS[model.__name__.lower()] = model
