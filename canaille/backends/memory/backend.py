import datetime
import uuid

from canaille.backends import BaseBackend


class Backend(BaseBackend):
    @classmethod
    def install(cls, config):
        pass

    def setup(self):
        pass

    def teardown(self):
        pass

    @classmethod
    def validate(cls, config):
        pass

    @classmethod
    def login_placeholder(cls):
        return ""

    def has_account_lockability(self):
        return True

    def get_user_from_login(self, login):
        from .models import User

        return self.get(User, user_name=login)

    def check_user_password(self, user, password):
        if password != user.password:
            return (False, None)

        if user.locked:
            return (False, "Your account has been locked.")

        return (True, None)

    def set_user_password(self, user, password):
        user.password = password
        self.save(user)

    def query(self, model, **kwargs):
        # if there is no filter, return all models
        if not kwargs:
            states = model.index().values()
            return [model(**state) for state in states]

        # get the ids from the attribute indexes
        ids = {
            id
            for attribute, values in kwargs.items()
            for value in model.serialize(model.listify(values))
            for id in model.attribute_index(attribute).get(value, [])
        }

        # get the states from the ids
        states = [model.index()[id] for id in ids]

        # initialize instances from the states
        instances = [model(**state) for state in states]
        for instance in instances:
            # TODO: maybe find a way to not initialize the cache in the first place?
            instance._cache = {}

        return instances

    def fuzzy(self, model, query, attributes=None, **kwargs):
        attributes = attributes or model.attributes
        instances = self.query(model, **kwargs)

        return [
            instance
            for instance in instances
            if any(
                query.lower() in value.lower()
                for attribute in attributes
                for value in model.listify(instance._state.get(attribute, []))
                if isinstance(value, str)
            )
        ]

    def get(self, model, identifier=None, /, **kwargs):
        if identifier:
            return (
                self.get(model, **{model.identifier_attribute: identifier})
                or self.get(model, id=identifier)
                or None
            )

        results = self.query(model, **kwargs)
        return results[0] if results else None

    def save(self, instance):
        if not instance.id:
            instance.id = str(uuid.uuid4())

        instance.last_modified = datetime.datetime.now(datetime.timezone.utc).replace(
            microsecond=0
        )
        if not instance.created:
            instance.created = instance.last_modified

        instance.index_delete()
        instance.index_save()
        instance._cache = {}

    def delete(self, instance):
        # run the instance delete callback if existing
        delete_callback = instance.delete() if hasattr(instance, "delete") else iter([])
        next(delete_callback, None)

        instance.index_delete()

        # run the instance delete callback again if existing
        next(delete_callback, None)

    def reload(self, instance):
        # run the instance reload callback if existing
        reload_callback = instance.reload() if hasattr(instance, "reload") else iter([])
        next(reload_callback, None)

        instance._state = BaseBackend.instance.get(
            instance.__class__, id=instance.id
        )._state
        instance._cache = {}

        # run the instance reload callback again if existing
        next(reload_callback, None)
