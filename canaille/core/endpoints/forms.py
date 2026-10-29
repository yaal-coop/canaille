import wtforms.form
import wtforms.validators
from flask import current_app
from flask import g
from flask_wtf.file import FileAllowed
from flask_wtf.file import FileField
from flask_wtf.file import FileSize
from wtforms_htmx_components import ComboboxMultiField

from canaille.app import models
from canaille.app.combobox import ChipsWidget
from canaille.app.combobox import ListboxWidget
from canaille.app.forms import DateTimeUTCField
from canaille.app.forms import Form
from canaille.app.forms import IDToModel
from canaille.app.forms import compromised_password_validator
from canaille.app.forms import email_validator
from canaille.app.forms import fieldlist_buttons
from canaille.app.forms import is_uri
from canaille.app.forms import password_length_validator
from canaille.app.forms import password_too_long_validator
from canaille.app.forms import phone_number
from canaille.app.forms import set_readonly
from canaille.app.forms import unique_values
from canaille.app.i18n import lazy_gettext as _
from canaille.app.i18n import native_language_name_from_code
from canaille.backends import Backend
from canaille.core.mails import RESET_CODE_LENGTH
from canaille.core.models import OTP_DIGITS
from canaille.core.photo import MAX_PHOTO_UPLOAD_SIZE
from canaille.core.validators import captcha_validator
from canaille.core.validators import email_has_user
from canaille.core.validators import existing_group_member
from canaille.core.validators import existing_login
from canaille.core.validators import group_owners
from canaille.core.validators import last_group_member
from canaille.core.validators import non_empty_groups
from canaille.core.validators import unique_email
from canaille.core.validators import unique_group
from canaille.core.validators import unique_user_name
from canaille.core.validators import user_not_in_group
from canaille.core.validators import valid_photo


class LoginForm(Form):
    login = wtforms.StringField(
        _("Login"),
        validators=[wtforms.validators.DataRequired(), existing_login],
        render_kw={
            "placeholder": _("jane.doe@example.com"),
            "spellcheck": "false",
            "autocorrect": "off",
            "inputmode": "email",
            "autocomplete": "section-login username",
            "icon": "user",
            "noindicator": True,
        },
    )
    remember = wtforms.BooleanField(
        _("Remember me"),
        default=True,
        render_kw={
            "title": _(
                "If unchecked, the session will close when the browser is closed"
            ),
            "container_class": "right aligned",
        },
    )


class CaptchaField(wtforms.StringField):
    """CAPTCHA field for security code input."""

    def __init__(self, **kwargs):
        super().__init__(
            _("Security code"),
            validators=[wtforms.validators.DataRequired(), captcha_validator],
            render_kw={
                "placeholder": _("Enter the security code displayed above"),
                "autocomplete": "off",
                "spellcheck": "false",
            },
            **kwargs,
        )


class UserForm(Form):
    """A form whose validators know the edited user, if any."""

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)


class GroupForm(Form):
    """A form whose validators know the edited group."""

    def __init__(self, *args, group, **kwargs):
        self.group = group
        super().__init__(*args, **kwargs)


class PasswordForm(Form):
    password = wtforms.PasswordField(
        _("Password"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={
            "autocomplete": "section-login current-password",
            "password_toggle": True,
            "noindicator": True,
        },
    )


class PasswordWithCaptchaForm(PasswordForm):
    captcha_token = wtforms.HiddenField()
    captcha = CaptchaField()


class ForgottenPasswordForm(Form):
    login = wtforms.StringField(
        _("Login"),
        validators=[wtforms.validators.DataRequired(), existing_login],
        render_kw={
            "placeholder": _("jane.doe@example.com"),
            "spellcheck": "false",
            "autocorrect": "off",
            "icon": "user",
        },
    )


class ForgottenPasswordCodeForm(Form):
    code = wtforms.StringField(
        _("Code"),
        validators=[
            wtforms.validators.DataRequired(),
            wtforms.validators.Length(min=RESET_CODE_LENGTH, max=RESET_CODE_LENGTH),
        ],
        render_kw={
            "placeholder": _("123456"),
            "spellcheck": "false",
            "autocorrect": "off",
            "icon": "key",
            "noindicator": True,
        },
    )


class PasswordResetForm(Form):
    password = wtforms.PasswordField(
        _("Password"),
        validators=[
            wtforms.validators.DataRequired(),
            password_length_validator,
            password_too_long_validator,
            compromised_password_validator,
        ],
        render_kw={
            "autocomplete": "new-password",
            "class": "password_strength",
            "hx-trigger": "input changed delay:500ms",
        },
    )
    confirmation = wtforms.PasswordField(
        _("Password confirmation"),
        validators=[
            wtforms.validators.EqualTo(
                "password", _("Password and confirmation do not match.")
            ),
        ],
        render_kw={
            "autocomplete": "new-password",
        },
    )


class FirstLoginForm(Form):
    pass


def available_language_choices():
    languages = [
        wtforms.SelectChoice(
            value=lang_code, label=native_language_name_from_code(lang_code)
        )
        for lang_code in g.available_language_codes
    ]
    languages.sort(key=lambda choice: (choice.value, choice.label))
    return [wtforms.SelectChoice(value="auto", label=_("Automatic"))] + languages


PROFILE_FORM_FIELDS = dict(
    user_name=wtforms.StringField(
        _("Username"),
        render_kw={"placeholder": _("jdoe"), "autocomplete": "username"},
        validators=[wtforms.validators.DataRequired(), unique_user_name],
    ),
    formatted_name=wtforms.StringField(_("Name")),
    title=wtforms.StringField(
        _("Title"),
        render_kw={
            "placeholder": _("Vice president"),
            "autocomplete": "organization-title",
        },
    ),
    given_name=wtforms.StringField(
        _("Given name"),
        render_kw={
            "placeholder": _("John"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    ),
    family_name=wtforms.StringField(
        _("Family Name"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={
            "placeholder": _("Doe"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    ),
    display_name=wtforms.StringField(
        _("Display Name"),
        validators=[wtforms.validators.Optional()],
        render_kw={
            "placeholder": _("Johnny"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    ),
    emails=wtforms.FieldList(
        wtforms.EmailField(
            _("Email addresses"),
            validators=[
                wtforms.validators.DataRequired(),
                email_validator,
                unique_email,
            ],
            description=_(
                "This email will be used as a recovery address to reset the password if needed"
            ),
            render_kw={
                "placeholder": _("jane.doe@example.com"),
                "spellcheck": "false",
                "autocorrect": "off",
                "autocomplete": "email",
            },
        ),
        min_entries=1,
        validators=[unique_values],
    ),
    phone_numbers=wtforms.FieldList(
        wtforms.TelField(
            _("Phone numbers"),
            render_kw={"placeholder": _("555-000-555"), "autocomplete": "tel"},
            validators=[wtforms.validators.Optional(), phone_number],
        ),
        min_entries=1,
        validators=[unique_values],
    ),
    formatted_address=wtforms.StringField(
        _("Address"),
        render_kw={
            "placeholder": _("132, Foobar Street, Gotham City 12401, XX"),
        },
    ),
    street=wtforms.StringField(
        _("Street"),
        render_kw={
            "placeholder": _("132, Foobar Street"),
            "autocomplete": "street-address",
        },
    ),
    postal_code=wtforms.StringField(
        _("Postal Code"),
        render_kw={
            "placeholder": "12401",
            "autocomplete": "postal-code",
        },
    ),
    locality=wtforms.StringField(
        _("Locality"),
        render_kw={
            "placeholder": _("Gotham City"),
            "autocomplete": "city",
        },
    ),
    region=wtforms.StringField(
        _("Region"),
        render_kw={
            "placeholder": _("North Pole"),
            "autocomplete": "country",
        },
    ),
    photo=FileField(
        _("Photo"),
        validators=[
            FileAllowed(["jpg", "jpeg", "png", "webp"]),
            FileSize(MAX_PHOTO_UPLOAD_SIZE),
            valid_photo,
        ],
        render_kw={
            "accept": "image/jpeg, image/png, image/webp",
            "display": False,
            "class": "photo-field",
        },
    ),
    photo_delete=wtforms.BooleanField(
        _("Delete the photo"),
        render_kw={"display": False, "class": "photo-delete-button"},
    ),
    password1=wtforms.PasswordField(
        _("Password"),
        validators=[
            wtforms.validators.Optional(),
            password_length_validator,
            password_too_long_validator,
            compromised_password_validator,
        ],
        render_kw={
            "autocomplete": "new-password",
            "class": "password_strength",
            "hx-trigger": "input changed delay:500ms",
            "noindicator": True,
        },
    ),
    password2=wtforms.PasswordField(
        _("Password confirmation"),
        validators=[
            wtforms.validators.EqualTo(
                "password1", message=_("Password and confirmation do not match.")
            )
        ],
        render_kw={
            "autocomplete": "new-password",
            "noindicator": True,
        },
    ),
    employee_number=wtforms.StringField(
        _("User number"),
        render_kw={
            "placeholder": _("1234"),
        },
    ),
    department=wtforms.StringField(
        _("Department"),
        render_kw={
            "placeholder": _("1234"),
        },
    ),
    organization=wtforms.StringField(
        _("Organization"),
        render_kw={
            "placeholder": _("Cogip LTD."),
            "autocomplete": "organization",
        },
    ),
    profile_url=wtforms.URLField(
        _("Website"),
        render_kw={
            "placeholder": _("https://mywebsite.example"),
        },
        validators=[wtforms.validators.Optional(), is_uri],
    ),
    preferred_language=wtforms.SelectField(
        _("Preferred language"),
        choices=available_language_choices,
        default="auto",
    ),
    groups=wtforms.SelectMultipleField(
        _("Groups"),
        default=[],
        choices=lambda: sorted(
            [
                wtforms.SelectChoice(value=group, label=group.display_name)
                for group in Backend.instance.query(models.Group)
            ],
            key=lambda choice: choice.value.id,
        ),
        render_kw={"placeholder": _("users, admins …")},
        coerce=IDToModel("Group"),
        validators=[non_empty_groups],
    ),
)


def build_profile_form(
    write_field_names,
    readonly_field_names,
    user=None,
    formdata=None,
    data=None,
    extra_fields=None,
):
    """Build a profile form with the fields that the ACL allow to read or write."""
    if "password" in write_field_names:
        write_field_names = write_field_names | {"password1", "password2"}

    if "photo" in write_field_names:
        write_field_names = write_field_names | {"photo_delete"}

    fields = {
        name: PROFILE_FORM_FIELDS.get(name)
        for name in write_field_names | readonly_field_names
        if PROFILE_FORM_FIELDS.get(name)
    }

    if "groups" in fields and not Backend.instance.query(models.Group):
        del fields["groups"]

    if "groups" in fields:
        fields["groups"] = groups_combobox(validators=[non_empty_groups])

    if current_app.features.has_account_lockability:  # pragma: no branch
        fields["lock_date"] = DateTimeUTCField(
            _("Account expiration"),
            validators=[wtforms.validators.Optional()],
            format=[
                "%Y-%m-%d %H:%M",
                "%Y-%m-%dT%H:%M",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
            ],
        )

    for list_name in ("emails", "phone_numbers"):
        if list_name in fields and list_name in write_field_names:
            fields[f"add_{list_name}"], fields[f"del_{list_name}"] = fieldlist_buttons(
                list_name
            )

    fields.update(extra_fields or {})
    form = type("ProfileForm", (UserForm,), fields)(formdata, data=data, user=user)
    for field in form:
        if field.name in readonly_field_names - write_field_names:
            set_readonly(field)

    return form


def captcha_fields():
    """Return the CAPTCHA fields to add to a dynamically built form."""
    return {"captcha_token": wtforms.HiddenField(), "captcha": CaptchaField()}


def model_combobox(
    label,
    model_name,
    attributes,
    describe,
    validators=(),
    exclude=None,
    filter=None,
    **kwargs,
):
    """Return a combobox field that picks model instances by their attributes.

    The instances in ``exclude(form)`` are not suggested. The suggestions only
    match the ``filter(form)`` attributes, and are sorted by their description.
    """

    def model():
        return getattr(models, model_name)

    def suggest(query, form):
        excluded = exclude(form) if exclude else ()
        filters = filter(form) if filter else {}
        instances = (
            Backend.instance.fuzzy(model(), query, attributes, **filters)
            if query
            else Backend.instance.query(model(), **filters)
        )
        choices = (
            wtforms.SelectChoice(instance.id, describe(instance))
            for instance in instances
            if instance not in excluded
        )
        return sorted(choices, key=lambda choice: choice.label.casefold())

    def label_for(instance_id):
        instance = Backend.instance.get(model(), id=instance_id)
        return describe(instance) if instance else instance_id

    def coerce(instance_id):
        if instance := Backend.instance.get(model(), id=instance_id):
            return instance

        raise ValueError(instance_id)

    return ComboboxMultiField(
        label,
        suggest=suggest,
        label_for=label_for,
        coerce=coerce,
        value_for=lambda instance: instance.id,
        validators=list(validators),
        search_label=_("Search"),
        listbox_widget=ListboxWidget(),
        chips_widget=ChipsWidget(),
        **kwargs,
    )


def groups_combobox(validators=()):
    """Return a combobox field that picks groups by their name."""
    return model_combobox(
        _("Groups"),
        "Group",
        ["display_name"],
        lambda group: group.display_name,
        validators=validators,
        placeholder=_("users, admins …"),
    )


def describe_user(user):
    """Return the name of ``user``, with an email or a user name to tell homonyms apart."""
    name = user.formatted_name or user.user_name
    detail = user.emails[0] if user.emails else user.user_name
    return name if detail == name else f"{name} ({detail})"


def group_members_combobox(label, validators=()):
    """Return a combobox field that picks users who are not members of the edited group yet.

    The suggestions list all users, so this is for users who can manage all groups.
    """
    return model_combobox(
        label,
        "User",
        ["user_name", "formatted_name", "emails"],
        describe_user,
        validators=validators,
        exclude=lambda form: form.group.members if form.group else (),
        placeholder=_("Jane Doe, jane.doe@example.com …"),
    )


def group_owners_combobox(validators=(), filter=None, **kwargs):
    """Return a combobox field that picks the owners of a group."""
    return model_combobox(
        _("Owners"),
        "User",
        ["user_name", "formatted_name", "emails"],
        describe_user,
        validators=validators,
        filter=filter,
        placeholder=_("Jane Doe, jane.doe@example.com …"),
        **kwargs,
    )


class CreateGroupForm(GroupForm):
    """The group creation form."""

    display_name = wtforms.StringField(
        _("Name"),
        validators=[wtforms.validators.DataRequired(), unique_group],
        render_kw={
            "placeholder": _("group"),
        },
    )
    description = wtforms.StringField(
        _("Description"),
        validators=[wtforms.validators.Optional()],
    )


class EditGroupForm(GroupForm):
    """The group edition form.

    The validators know the user who edits the group.
    """

    def __init__(self, *args, editor, **kwargs):
        self.editor = editor
        super().__init__(*args, **kwargs)

    display_name = wtforms.StringField(
        _("Name"),
        validators=[
            wtforms.validators.DataRequired(),
            wtforms.validators.ReadOnly(),
        ],
        render_kw={
            "readonly": "true",
        },
    )
    description = wtforms.StringField(
        _("Description"),
        validators=[wtforms.validators.Optional()],
    )
    owners = group_owners_combobox(
        validators=[group_owners],
        filter=lambda form: {"groups": form.group},
        min_query_length=0,
        description=_("Only members can be owners."),
    )


class CreateGroupWithMembersForm(CreateGroupForm):
    """The group creation form, with the members and the owners to add."""

    members = group_members_combobox(_("Members"))
    owners = group_owners_combobox()


class AddGroupMembersForm(GroupForm):
    """The form that adds members to a group."""

    new_members = group_members_combobox(
        _("Add members"), validators=[wtforms.validators.DataRequired()]
    )


class DeleteGroupMemberForm(GroupForm):
    member = wtforms.StringField(
        filters=[IDToModel("User", raise_on_errors=False)],
        validators=[existing_group_member, last_group_member],
    )


class GroupInvitationForm(GroupForm):
    """The group invitation form."""

    email = wtforms.EmailField(
        _("Email address"),
        validators=[
            wtforms.validators.DataRequired(),
            email_validator,
            email_has_user,
            user_not_in_group,
        ],
        render_kw={
            "placeholder": _("jane.doe@example.com"),
            "spellcheck": "false",
            "autocorrect": "off",
            "icon": "email",
        },
    )
    invite_as_owner = wtforms.BooleanField(
        _("Invite as owner"),
        default=False,
    )


class JoinForm(UserForm):
    email = wtforms.EmailField(
        _("Email address"),
        validators=[
            wtforms.validators.DataRequired(),
            email_validator,
        ],
        render_kw={
            "placeholder": _("jane.doe@example.com"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    )

    def validate_email(form, field):
        if not current_app.config["CANAILLE"]["HIDE_INVALID_LOGINS"]:
            unique_email(form, field)


class JoinFormWithCaptcha(JoinForm):
    captcha_token = wtforms.HiddenField()
    captcha = CaptchaField()


class InvitationForm(UserForm):
    """The user invitation form."""

    user_name = wtforms.StringField(
        _("User name"),
        render_kw={"placeholder": _("jdoe"), "icon": "user"},
        validators=[wtforms.validators.DataRequired(), unique_user_name],
    )
    user_name_editable = wtforms.BooleanField(_("Username editable by the invitee"))
    email = wtforms.EmailField(
        _("Email address"),
        validators=[
            wtforms.validators.DataRequired(),
            email_validator,
            unique_email,
        ],
        render_kw={
            "placeholder": _("jane.doe@example.com"),
            "spellcheck": "false",
            "autocorrect": "off",
            "icon": "email",
        },
    )
    groups = groups_combobox()


class EmailConfirmationForm(UserForm):
    old_emails = wtforms.FieldList(
        wtforms.EmailField(
            validators=[wtforms.validators.ReadOnly()],
            description=_(
                "This email will be used as a recovery address to reset the password if needed"
            ),
            render_kw={
                "placeholder": _("jane.doe@example.com"),
                "spellcheck": "false",
                "autocorrect": "off",
                "readonly": "true",
            },
        ),
        label=_("Email addresses"),
    )
    new_email = wtforms.EmailField(
        _("New email address"),
        validators=[
            wtforms.validators.DataRequired(),
            email_validator,
            unique_email,
        ],
        render_kw={
            "placeholder": _("jane.doe@example.com"),
            "spellcheck": "false",
            "autocorrect": "off",
            "noindicator": True,
            "action_button": {
                "value": "add_email",
                "icon": "send",
                "label": _("Verify"),
                "title": _("Send a verification email to validate this address."),
            },
        },
    )
    email_remove = wtforms.ButtonField()


class Fido2CredentialsForm(Form):
    fido2_rename_credential = wtforms.ButtonField()
    fido2_confirm_credential = wtforms.ButtonField()


class TwoFactorForm(Form):
    otp = wtforms.StringField(
        _("Passcode"),
        validators=[
            wtforms.validators.DataRequired(),
            wtforms.validators.Length(min=OTP_DIGITS, max=OTP_DIGITS),
        ],
        render_kw={
            "placeholder": _("123456"),
            "spellcheck": "false",
            "autocorrect": "off",
            "autocomplete": "one-time-code",
            "icon": "key",
            "noindicator": True,
        },
    )
