import datetime
import io
from dataclasses import astuple
from dataclasses import dataclass
from importlib import metadata

import wtforms
from flask import Blueprint
from flask import Response
from flask import abort
from flask import current_app
from flask import flash
from flask import g
from flask import redirect
from flask import request
from flask import send_file
from flask import session
from flask import url_for
from itsdangerous import BadSignature
from itsdangerous import URLSafeSerializer
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.datastructures import FileStorage

from canaille.app import b64_to_obj
from canaille.app import build_hash
from canaille.app import default_fields
from canaille.app import models
from canaille.app import obj_to_b64
from canaille.app.flask import partial_request_trigger
from canaille.app.flask import render_htmx_template
from canaille.app.flask import request_is_partial
from canaille.app.flask import smtp_needed
from canaille.app.flask import user_needed
from canaille.app.forms import IDToModel
from canaille.app.forms import TableForm
from canaille.app.forms import compromised_password_validator
from canaille.app.forms import is_readonly
from canaille.app.forms import password_length_validator
from canaille.app.forms import password_too_long_validator
from canaille.app.forms import set_readonly
from canaille.app.forms import set_writable
from canaille.app.i18n import gettext as _
from canaille.app.i18n import reload_translations
from canaille.app.session import login_user
from canaille.app.session import logout_user
from canaille.app.templating import render_template
from canaille.backends import Backend
from canaille.core.captcha import generate_audio_captcha
from canaille.core.captcha import generate_captcha
from canaille.core.endpoints.forms import EmailConfirmationForm
from canaille.core.endpoints.forms import InvitationForm
from canaille.core.endpoints.forms import JoinForm
from canaille.core.endpoints.forms import JoinFormWithCaptcha
from canaille.core.endpoints.forms import PasswordResetForm
from canaille.core.endpoints.forms import add_captcha_fields
from canaille.core.endpoints.forms import build_profile_form
from canaille.core.mails import send_confirmation_email
from canaille.core.mails import send_invitation_mail
from canaille.core.mails import send_registration_mail
from canaille.core.utils import guess_image_mimetype

from . import auth

bp = Blueprint("account", __name__)
bp.register_blueprint(auth.bp)


@bp.route("/")
def index():
    if not g.session:
        return redirect(url_for("core.auth.login"))

    user = g.session.user
    if user.can_edit_self or user.can_manage_users:
        return redirect(url_for("core.account.profile_edition", edited_user=user))

    if current_app.features.has_oidc and user.can_use_oidc:
        return redirect(url_for("oidc.consents.consents"))

    return redirect(url_for("core.account.about"))


@bp.route("/join", methods=("GET", "POST"))
def join():
    if not current_app.features.has_registration:
        abort(404)

    if not current_app.features.has_email_confirmation:
        return redirect(url_for(".registration"))

    if g.session:
        abort(403)

    if current_app.features.has_captcha:
        form = JoinFormWithCaptcha(request.form or None)
    else:
        form = JoinForm(request.form or None)

    def render_join_template():
        captcha_data = None
        if current_app.features.has_captcha:
            captcha_data = generate_captcha()
            form["captcha_token"].data = captcha_data["token"]
        return render_template(
            "core/join.html", form=form, menu=False, captcha_data=captcha_data
        )

    if request.form.get("action") == "refresh_captcha":
        old_token = request.form.get("captcha_token")
        if old_token:
            session.pop(f"captcha_{old_token}", None)
        return render_join_template()

    if not request.form:
        return render_join_template()

    if not form.validate():
        return render_join_template()

    if Backend.instance.query(models.User, emails=form.email.data):
        flash(
            _("You will receive soon an email to continue the registration process."),
            "success",
        )
        return render_template(
            "core/join.html", form=form, menu=False, captcha_data=None
        )

    payload = RegistrationPayload(
        creation_date_isoformat=datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        user_name="",
        user_name_editable=True,
        email=form.email.data,
        groups=[],
    )

    registration_url = url_for(
        "core.account.registration",
        data=payload.b64(),
        hash=payload.build_hash(),
        _external=True,
    )

    send_registration_mail(form.email.data, registration_url)
    flash(
        _("You will receive soon an email to continue the registration process."),
        "info",
    )

    return render_template("core/join.html", form=form, menu=False, captcha_data=None)


@bp.route("/about")
def about():
    version = metadata.version("canaille")
    return render_template("core/about.html", version=version)


@bp.route("/captcha-audio/<token>")
def captcha_audio(token):
    """Serve audio CAPTCHA."""
    if not current_app.features.has_captcha:  # pragma: no cover
        abort(404)

    session_key = f"captcha_{token}"
    text = session.get(session_key)

    if not text:
        abort(404)

    etag = f'"{token}"'

    if request.headers.get("If-None-Match") == etag:
        return Response(status=304)

    audio_data = generate_audio_captcha(text)
    response = Response(audio_data, mimetype="audio/wav")
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "private, max-age=600"
    return response


@bp.route("/users", methods=["GET", "POST"])
@user_needed("manage_users")
def users(user):
    table_form = TableForm(
        models.User,
        fields=user.readable_fields | user.writable_fields,
        formdata=request.form,
    )
    if request.form and not table_form.validate():
        abort(404)

    return render_htmx_template(
        "core/users.html",
        menuitem="users",
        table_form=table_form,
    )


@dataclass
class VerificationPayload:
    creation_date_isoformat: str

    @property
    def creation_date(self):
        return datetime.datetime.fromisoformat(self.creation_date_isoformat)

    def has_expired(self):
        return datetime.datetime.now(
            datetime.timezone.utc
        ) - self.creation_date > datetime.timedelta(
            seconds=current_app.config["CANAILLE"]["INVITATION_EXPIRATION"]
        )

    def b64(self):
        return obj_to_b64(astuple(self))

    def build_hash(self):
        return build_hash(*astuple(self))


@dataclass
class EmailConfirmationPayload(VerificationPayload):
    identifier: str
    email: str


@dataclass
class RegistrationPayload(VerificationPayload):
    user_name: str
    user_name_editable: bool
    email: str
    groups: list[str]


@dataclass
class GroupInvitationPayload:
    expiration_date_isoformat: str
    group_id: str
    invited_user_id: str

    @property
    def expiration_date(self):
        return datetime.datetime.fromisoformat(self.expiration_date_isoformat)

    def has_expired(self):
        return datetime.datetime.now(datetime.timezone.utc) > self.expiration_date

    def b64(self):
        return obj_to_b64(astuple(self))

    def build_hash(self):
        return build_hash(*astuple(self))


@bp.route("/invite", methods=["GET", "POST"])
@smtp_needed()
@user_needed("manage_users")
def user_invitation(user):
    form = InvitationForm(request.form or None)
    email_sent = None
    registration_url = None
    form_validated = False
    if request.form and form.validate():
        form_validated = True
        payload = RegistrationPayload(
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
            form.user_name.data,
            form.user_name_editable.data,
            form.email.data,
            [group.id for group in form.groups.data],
        )
        registration_url = url_for(
            "core.account.registration",
            data=payload.b64(),
            hash=payload.build_hash(),
            _external=True,
        )

        if request.form["action"] == "send":
            email_sent = send_invitation_mail(form.email.data, registration_url)

    return render_template(
        "core/invite.html",
        form=form,
        menuitems="users",
        form_validated=form_validated,
        email_sent=email_sent,
        registration_url=registration_url,
    )


@bp.route("/register", methods=["GET", "POST"])
@bp.route("/register/<data>/<hash>", methods=["GET", "POST"])
def registration(data=None, hash=None):
    if not data:
        payload = None
        if (
            not current_app.features.has_registration
            or current_app.features.has_email_confirmation
        ):
            abort(403)

    else:
        data_obj = b64_to_obj(data)
        if data_obj is None:
            flash(
                _("The registration link that brought you here was invalid."),
                "error",
            )
            return redirect(url_for("core.account.index"))
        payload = RegistrationPayload(*data_obj)

        if payload.has_expired():
            flash(
                _("The registration link that brought you here has expired."),
                "error",
            )
            return redirect(url_for("core.account.index"))

        if payload.user_name and Backend.instance.get(
            models.User, user_name=payload.user_name
        ):
            flash(
                _("Your account has already been created."),
                "error",
            )
            return redirect(url_for("core.account.index"))

        if hash != payload.build_hash():
            flash(
                _("The registration link that brought you here was invalid."),
                "error",
            )
            return redirect(url_for("core.account.index"))

    if user := g.session and g.session.user:
        flash(
            _("You are already logged in, you cannot create an account."),
            "error",
        )
        return redirect(url_for("core.account.index"))

    if payload:
        data = {
            "user_name": payload.user_name,
            "emails": [payload.email],
            "groups": [
                Backend.instance.get(models.Group, id=group_id)
                for group_id in payload.groups
            ],
        }

    emails_readonly = current_app.features.has_email_confirmation
    readable_fields, writable_fields = default_fields()

    form = build_profile_form(writable_fields, readable_fields)
    if "groups" not in form and payload and payload.groups:
        form["groups"] = wtforms.SelectMultipleField(
            _("Groups"),
            choices=[
                (group, group.display_name)
                for group in Backend.instance.query(models.Group)
            ],
            coerce=IDToModel("Group"),
        )
        set_readonly(form["groups"])

    if (
        current_app.features.has_captcha
        and not current_app.features.has_email_confirmation
    ):
        add_captcha_fields(form)

    form.process(CombinedMultiDict((request.files, request.form)) or None, data=data)

    if is_readonly(form["user_name"]) and (not payload or payload.user_name_editable):
        set_writable(form["user_name"])

    if not is_readonly(form["emails"]) and emails_readonly:
        set_readonly(form["emails"])

    form["password1"].validators = [
        wtforms.validators.DataRequired(),
        password_length_validator,
        password_too_long_validator,
        compromised_password_validator,
    ]
    form["password2"].validators = [
        wtforms.validators.DataRequired(),
        wtforms.validators.EqualTo(
            "password1", message=_("Password and confirmation do not match.")
        ),
    ]
    form["password1"].flags.required = True
    form["password2"].flags.required = True

    def render_registration_template():
        captcha_data = None
        if (
            current_app.features.has_captcha
            and not current_app.features.has_email_confirmation
        ):
            captcha_data = generate_captcha()
            form["captcha_token"].data = captcha_data["token"]

        return render_template(
            "core/account/add.html",
            form=form,
            menu=False,
            captcha_data=captcha_data,
        )

    if request.form.get("action") == "refresh_captcha":
        old_token = request.form.get("captcha_token")
        if old_token:
            session.pop(f"captcha_{old_token}", None)
        return render_registration_template()

    if not request.form or form.handle_fieldlist_operation():
        return render_registration_template()

    if not form.validate():
        flash(
            _("Your account couldn't be created. Please check the form and try again."),
            "error",
        )
        return render_registration_template()

    user = profile_create(current_app, form)
    login_user(user)
    flash(_("Your account has been created successfully."), "success")
    return redirect(
        session.pop(
            "redirect-after-login",
            url_for("core.account.profile_edition", edited_user=user),
        )
    )


@bp.route("/email-confirmation/<data>/<hash>")
def email_confirmation(data, hash):
    data_obj = b64_to_obj(data)
    if data_obj is None:
        flash(
            _("The email confirmation link that brought you here is invalid."),
            "error",
        )
        return redirect(url_for("core.account.index"))
    confirmation_obj = EmailConfirmationPayload(*data_obj)

    if confirmation_obj.has_expired():
        flash(
            _("The email confirmation link that brought you here has expired."),
            "error",
        )
        return redirect(url_for("core.account.index"))

    if hash != confirmation_obj.build_hash():
        flash(
            _("The invitation link that brought you here was invalid."),
            "error",
        )
        return redirect(url_for("core.account.index"))

    user = Backend.instance.get(models.User, confirmation_obj.identifier)
    if not user:
        flash(
            _("The email confirmation link that brought you here is invalid."),
            "error",
        )
        return redirect(url_for("core.account.index"))

    if confirmation_obj.email in user.emails or []:
        flash(
            _("This email address has already been confirmed."),
            "error",
        )
        return redirect(url_for("core.account.index"))

    if Backend.instance.query(models.User, emails=confirmation_obj.email):
        flash(
            _("This email address is already associated with another account."),
            "error",
        )
        return redirect(url_for("core.account.index"))

    user.emails = (user.emails or []) + [confirmation_obj.email]
    Backend.instance.save(user)
    flash(_("Your email address has been confirmed."), "success")
    return redirect(url_for("core.account.index"))


@bp.route("/profile", methods=("GET", "POST"))
@user_needed("manage_users")
def profile_creation(user):
    form = build_profile_form(user.writable_fields, user.readable_fields)
    form.process(CombinedMultiDict((request.files, request.form)) or None)

    for field in form:
        if is_readonly(field):
            set_writable(field)

    if not request.form or form.handle_fieldlist_operation():
        return render_template(
            "core/account/add.html",
            form=form,
            menuitem="users",
            captcha_data=None,
        )

    if not form.validate():
        flash(
            _("The account couldn't be created. Please check the form and try again."),
            "error",
        )
        return render_template(
            "core/account/add.html",
            form=form,
            menuitem="users",
            captcha_data=None,
        )

    user = profile_create(current_app, form)
    flash(_("User account creation succeeded."), "success")
    return redirect(url_for("core.account.profile_edition", edited_user=user))


def profile_create(current_app, form):
    user = models.User()
    for attribute in form:
        if attribute.name in models.User.attributes:
            if isinstance(attribute.data, FileStorage):
                data = attribute.data.stream.read()
            else:
                data = attribute.data

            setattr(user, attribute.name, data)

        if "photo" in form and form["photo_delete"].data:
            user.photo = None

    given_name = user.given_name if user.given_name else ""
    family_name = user.family_name if user.family_name else ""
    user.formatted_name = f"{given_name} {family_name}".strip()
    Backend.instance.save(user)

    if form["password1"].data:
        Backend.instance.set_user_password(user, form["password1"].data)
        Backend.instance.save(user)

    return user


def _build_profile_form(user, edited_user, emails_readonly):
    available_fields = {
        "formatted_name",
        "title",
        "given_name",
        "family_name",
        "display_name",
        "emails",
        "phone_numbers",
        "formatted_address",
        "street",
        "postal_code",
        "locality",
        "region",
        "photo",
        "photo_delete",
        "employee_number",
        "department",
        "profile_url",
        "preferred_language",
        "organization",
    }
    if emails_readonly:
        available_fields.remove("emails")

    readable_fields = user.readable_fields & available_fields
    writable_fields = user.writable_fields & available_fields
    data = {
        field: getattr(edited_user, field)
        for field in writable_fields | readable_fields
        if hasattr(edited_user, field) and getattr(edited_user, field)
    }
    request_data = CombinedMultiDict((request.files, request.form))
    profile_form = build_profile_form(writable_fields, readable_fields)
    profile_form.process(request_data or None, data=data)
    profile_form.user = edited_user
    profile_form.render_field_macro_file = "core/partial/profile_field.html"
    profile_form.render_field_extra_context = {
        "user": user,
        "edited_user": edited_user,
    }
    return profile_form


def _build_emails_form(edited_user, has_smtp):
    emails_form = EmailConfirmationForm(
        request.form or None, data={"old_emails": edited_user.emails or []}
    )
    emails_form.add_email_button = has_smtp
    emails_form.render_field_macro_file = "core/partial/emails_field.html"
    return emails_form


def _handle_edit_profile(
    user, edited_user, profile_form, has_email_changed, render_context
):
    if not profile_form.validate():
        flash(
            _("Your changes couldn't be saved. Please check the form and try again."),
            "error",
        )
        return render_template("core/account/edit.html", **render_context)

    for field in profile_form:
        if field.name in edited_user.attributes and field.name in user.writable_fields:
            if isinstance(field, wtforms.FieldList):
                data = [value for value in field.data if value] or None
            elif isinstance(field.data, FileStorage):
                data = field.data.stream.read()
            else:
                data = field.data
            setattr(edited_user, field.name, data)

    if "photo" in profile_form and profile_form["photo_delete"].data:
        edited_user.photo = None

    if "preferred_language" in request.form:
        reload_translations()
        if profile_form["preferred_language"].data == "auto":
            edited_user.preferred_language = None

    Backend.instance.save(edited_user)
    Backend.instance.reload(user)

    if has_email_changed:
        current_app.logger.security(f"Updated email for {edited_user.user_name}")

    flash(_("Profile updated successfully."), "success")
    return redirect(url_for("core.account.profile_edition", edited_user=edited_user))


def _handle_add_email(edited_user, emails_form, render_context):
    if not emails_form.validate():
        flash(
            _("This email couldn't be added. Please check the format and try again."),
            "error",
        )
        return render_template("core/account/edit.html", **render_context)

    email_confirmation = EmailConfirmationPayload(
        datetime.datetime.now(datetime.timezone.utc).isoformat(),
        edited_user.identifier,
        emails_form.new_email.data,
    )
    email_confirmation_url = url_for(
        "core.account.email_confirmation",
        data=email_confirmation.b64(),
        hash=email_confirmation.build_hash(),
        _external=True,
    )
    current_app.logger.debug(
        f"Attempt to send a verification mail with link: {email_confirmation_url}"
    )
    send_confirmation_email(emails_form.new_email.data, email_confirmation_url)

    flash(
        _(
            "Sending an email to this email address. "
            "Please check your inbox and click on the verification link it contains"
        ),
        "info",
    )
    return redirect(url_for("core.account.profile_edition", edited_user=edited_user))


def _handle_remove_email(edited_user, email, render_context):
    if email not in (edited_user.emails or []):
        flash(_("This email couldn't be removed."), "error")
        return render_template("core/account/edit.html", **render_context)

    if not edited_user.emails or len(edited_user.emails) == 1:
        flash(_("This email couldn't be removed. You must keep at least one."), "error")
        return render_template("core/account/edit.html", **render_context)

    edited_user.emails = [m for m in edited_user.emails if m != email]
    Backend.instance.save(edited_user)

    flash(_("The email has been successfully deleted."), "success")
    return redirect(url_for("core.account.profile_edition", edited_user=edited_user))


@bp.route("/profile/<user:edited_user>", methods=("GET", "POST"))
@user_needed()
def profile_edition(user, edited_user):
    if not user.can_manage_users and not (
        user.can_edit_self and edited_user.id == user.id
    ):
        abort(404)

    menuitem = "profile" if edited_user.id == user.id else "users"
    emails_readonly = (
        current_app.features.has_email_confirmation and not user.can_manage_users
    )

    profile_form = _build_profile_form(user, edited_user, emails_readonly)
    emails_form = (
        _build_emails_form(edited_user, current_app.features.has_smtp)
        if emails_readonly
        else None
    )

    has_email_changed = "emails" in profile_form and set(
        profile_form["emails"].data
    ) != set(user.emails or [])

    render_context = {
        "menuitem": menuitem,
        "edited_user": edited_user,
        "profile_form": profile_form,
        "emails_form": emails_form,
    }

    if not request.form or profile_form.handle_fieldlist_operation():
        return render_template("core/account/edit.html", **render_context)

    action = request.form.get("action")

    if action == "edit-profile" or (
        request_is_partial() and partial_request_trigger() in profile_form
    ):
        return _handle_edit_profile(
            user, edited_user, profile_form, has_email_changed, render_context
        )

    if action == "add_email" or (
        request_is_partial()
        and emails_form
        and partial_request_trigger() in emails_form
    ):
        return _handle_add_email(edited_user, emails_form, render_context)

    if request.form.get("email_remove"):
        return _handle_remove_email(
            edited_user, request.form.get("email_remove"), render_context
        )

    abort(400, f"bad form action: {action}")


def _handle_delete_actions(user, edited_user, action):
    if action == "delete-confirm":
        return render_template(
            "core/modals/delete-account.html", edited_user=edited_user
        )

    else:  # delete-execute
        self_deletion = user.id == edited_user.id
        if self_deletion:
            logout_user()

        flash(
            _(
                "The user %(user)s has been successfully deleted",
                user=edited_user.formatted_name,
            ),
            "success",
        )
        Backend.instance.delete(edited_user)
        current_app.logger.security(
            f"Deleted user {edited_user.id} by {user.id}"
            if not self_deletion
            else f"User {edited_user.id} deleted their own account"
        )

        if self_deletion:
            return redirect(url_for("core.account.index"))
        return redirect(url_for("core.account.users"))


def _handle_lock_actions(user, edited_user, action):
    if action == "lock-confirm":
        return render_template("core/modals/lock-account.html", edited_user=edited_user)

    elif action == "lock-execute":
        flash(_("The account has been locked."), "success")
        edited_user.lock_date = datetime.datetime.now(datetime.timezone.utc)
        Backend.instance.save(edited_user)
        return _handle_profile_settings_edit(user, edited_user)

    else:  # unlock
        flash(_("The account has been unlocked."), "success")
        edited_user.lock_date = None
        Backend.instance.save(edited_user)
        return _handle_profile_settings_edit(user, edited_user)


@bp.route("/profile/<user:edited_user>/settings", methods=("GET", "POST"))
@user_needed()
def profile_settings(user, edited_user):
    if not user.can_manage_users and not (
        user.can_edit_self and edited_user.id == user.id
    ):
        abort(404)

    if (
        request.method == "GET"
        or request.form.get("action") == "edit-settings"
        or request_is_partial()
    ):
        return _handle_profile_settings_edit(user, edited_user)

    action = request.form.get("action")

    if action in ("delete-confirm", "delete-execute"):
        return _handle_delete_actions(user, edited_user, action)

    if current_app.features.has_account_lockability and action in (
        "lock-confirm",
        "lock-execute",
        "unlock",
    ):
        return _handle_lock_actions(user, edited_user, action)

    abort(400, f"bad form action: {action}")


def _handle_profile_settings_edit(editor, edited_user):
    menuitem = "profile" if editor.id == editor.id else "users"
    fields = editor.readable_fields | editor.writable_fields

    available_fields = {"groups", "user_name", "lock_date"}
    data = {
        k: getattr(edited_user, k)[0]
        if getattr(edited_user, k) and isinstance(getattr(edited_user, k), list)
        else getattr(edited_user, k) or ""
        for k in fields
        if hasattr(edited_user, k) and k in available_fields
    }

    data["groups"] = edited_user.groups

    form = build_profile_form(
        editor.writable_fields & available_fields,
        editor.readable_fields & available_fields,
        edited_user,
    )
    form.process(CombinedMultiDict((request.files, request.form)) or None, data=data)
    if (
        request.form
        and request.form.get("action") == "edit-settings"
        or request_is_partial()
    ):
        if not form.validate():
            flash(
                _(
                    "Your changes couldn't be saved. "
                    "Please check the form and try again."
                ),
                "error",
            )

        else:
            for attribute in form:
                if attribute.name in available_fields & editor.writable_fields:
                    setattr(edited_user, attribute.name, attribute.data)

            Backend.instance.save(edited_user)
            flash(_("Profile updated successfully."), "success")
            return redirect(
                url_for("core.account.profile_settings", edited_user=edited_user)
            )

    return render_template(
        "core/account/settings.html",
        form=form,
        menuitem=menuitem,
        edited_user=edited_user,
        self_deletion=edited_user.can_delete_account,
    )


@bp.route("/impersonate/<user:puppet>")
@user_needed("impersonate_users")
def impersonate(user, puppet):
    if puppet.locked:
        abort(403, _("Locked users cannot be impersonated."))

    login_user(puppet, remember=False)
    current_app.logger.security(f"User {user.id} impersonated {puppet.id}")
    flash(
        _("Connection successful. Welcome %(user)s", user=puppet.name),
        "success",
    )
    return redirect(url_for("core.account.index"))


@bp.app_template_filter()
def photo_url(user):
    serializer = URLSafeSerializer(current_app.config["SECRET_KEY"], salt="photo")
    return url_for("core.account.photo", token=serializer.dumps(user.identifier))


@bp.route("/photo/<token>")
def photo(token):
    serializer = URLSafeSerializer(current_app.config["SECRET_KEY"], salt="photo")
    try:
        identifier = serializer.loads(token)
    except BadSignature:
        abort(404)

    user = Backend.instance.get(models.User, identifier)
    if not user or not user.photo:
        abort(404)

    etag = build_hash(user.identifier, user.last_modified.isoformat())
    if request.if_none_match and etag in request.if_none_match:
        return "", 304
    if request.if_modified_since and request.if_modified_since >= user.last_modified:
        return "", 304

    mimetype = guess_image_mimetype(user.photo)
    return send_file(
        io.BytesIO(user.photo),
        mimetype=mimetype,
        last_modified=user.last_modified,
        etag=etag,
    )


@bp.route("/reset/<user:user>", methods=["GET", "POST"])
def reset(user):
    form = PasswordResetForm(request.form)
    if not g.session or user != g.session.user or not user.has_expired_password():
        abort(403)

    if request.form and form.validate():
        Backend.instance.set_user_password(user, form.password.data)
        login_user(user)
        flash(_("Your password has been updated successfully."), "success")
        return redirect(
            session.pop(
                "redirect-after-login",
                url_for("core.account.profile_edition", edited_user=user),
            )
        )

    return render_template(
        "core/auth/reset-password.html", form=form, user=user, token=None
    )
