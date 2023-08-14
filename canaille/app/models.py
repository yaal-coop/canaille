MODELS = {}


def __getattr__(name):
    if name in MODELS:
        return MODELS[name]


def register(model):
    MODELS[model.__name__] = model
