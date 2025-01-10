import binascii
import datetime
import io
from dataclasses import astuple
from dataclasses import dataclass
from importlib import metadata

import wtforms
from flask import Blueprint
from flask import abort
from flask import current_app
from flask import flash
from flask import g
from flask import redirect
from flask import request
from flask import send_file
from flask import session
from flask import url_for
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.datastructures import FileStorage

from canaille.app import b64_to_obj
from canaille.app import build_hash
from canaille.app import default_fields
from canaille.app import models
from canaille.app import obj_to_b64
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
from canaille.app.session import current_user
from canaille.app.session import login_user
from canaille.app.session import logout_user
from canaille.app.templating import render_template
from canaille.backends import Backend

from ..mails import send_confirmation_email
from ..mails import send_invitation_mail
from ..mails import send_password_initialization_mail
from ..mails import send_password_reset_mail
from ..mails import send_registration_mail
from .forms import EmailConfirmationForm
from .forms import InvitationForm
from .forms import JoinForm
from .forms import PasswordResetForm
from .forms import build_profile_form

bp = Blueprint("account", __name__)


@bp.route("/")
def index():
    user = current_user()

    if not user:
        return redirect(url_for("core.auth.login"))

    if user.can_edit_self or user.can_manage_users:
        return redirect(url_for("core.account.profile_edition", edited_user=user))

    if current_app.features.has_oidc and user.can_use_oidc:
        return redirect(url_for("oidc.consents.consents"))

    return redirect(url_for("core.account.about"))


@bp.route("/join", methods=("GET", "POST"))
def join():
    if not current_app.features.has_registration:
        abort(404)

    if not current_app.config["CANAILLE"]["EMAIL_CONFIRMATION"]:
        return redirect(url_for(".registration"))

    if current_user():
        abort(403)

    form = JoinForm(request.form or None)
    if request.form and form.validate():
        if Backend.instance.query(models.User, emails=form.email.data):
            flash(
                _(
                    "You will receive soon an email to continue the registration process."
                ),
                "success",
            )
            return render_template("core/join.html", form=form)

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

        if send_registration_mail(form.email.data, registration_url):
            flash(
                _(
                    "You will receive soon an email to continue the registration process."
                ),
                "success",
            )
        else:
            flash(
                _(
                    "An error happened while sending your registration mail. "
                    "Please try again in a few minutes. "
                    "If this still happens, please contact the administrators."
                ),
                "error",
            )

    return render_template("core/join.html", form=form)


@bp.route("/about")
def about():
    version = metadata.version("canaille")
    return render_template("core/about.html", version=version)


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
        try:
            payload = RegistrationPayload(*b64_to_obj(data))
        except binascii.Error:
            flash(
                _("The registration link that brought you here was invalid."),
                "error",
            )
            return redirect(url_for("core.account.index"))

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

    user = current_user()
    if user:
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

    if not request.form or form.form_control():
        return render_template(
            "core/profile_add.html",
            form=form,
            menuitem="users",
        )

    if not form.validate():
        flash(_("User account creation failed."), "error")
        return render_template(
            "core/profile_add.html",
            form=form,
            menuitem="users",
        )

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
    try:
        confirmation_obj = EmailConfirmationPayload(*b64_to_obj(data))
    except:
        flash(
            _("The email confirmation link that brought you here is invalid."),
            "error",
        )
        return redirect(url_for("core.account.index"))

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

    if confirmation_obj.email in user.emails:
        flash(
            _("This address email have already been confirmed."),
            "error",
        )
        return redirect(url_for("core.account.index"))

    if Backend.instance.query(models.User, emails=confirmation_obj.email):
        flash(
            _("This address email is already associated with another account."),
            "error",
        )
        return redirect(url_for("core.account.index"))

    user.emails = user.emails + [confirmation_obj.email]
    Backend.instance.save(user)
    flash(_("Your email address have been confirmed."), "success")
    return redirect(url_for("core.account.index"))


@bp.route("/profile", methods=("GET", "POST"))
@user_needed("manage_users")
def profile_creation(user):
    form = build_profile_form(user.writable_fields, user.readable_fields)
    form.process(CombinedMultiDict((request.files, request.form)) or None)

    for field in form:
        if is_readonly(field):
            set_writable(field)

    if not request.form or form.form_control():
        return render_template(
            "core/profile_add.html",
            form=form,
            menuitem="users",
        )

    if not form.validate():
        flash(_("User account creation failed."), "error")
        return render_template(
            "core/profile_add.html",
            form=form,
            menuitem="users",
        )

    user = profile_create(current_app, form)
    flash(_("User account creation succeed."), "success")
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


def profile_edition_main_form(user, edited_user, emails_readonly):
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


def profile_edition_main_form_validation(user, edited_user, profile_form):
    for field in profile_form:
        if field.name in edited_user.attributes and field.name in user.writable_fields:
            if isinstance(field, wtforms.FieldList):
                # too bad wtforms cannot sanitize the list itself
                data = [value for value in field.data if value] or None
            elif isinstance(field.data, FileStorage):
                data = field.data.stream.read()
            else:
                data = field.data

            setattr(edited_user, field.name, data)

    if "photo" in profile_form and profile_form["photo_delete"].data:
        edited_user.photo = None

    if "preferred_language" in request.form:
        # Refresh the babel cache in case the lang is updated
        reload_translations()

        if profile_form["preferred_language"].data == "auto":
            edited_user.preferred_language = None

    Backend.instance.save(edited_user)
    Backend.instance.reload(g.user)


def profile_edition_emails_form(user, edited_user, has_smtp):
    emails_form = EmailConfirmationForm(
        request.form or None, data={"old_emails": edited_user.emails}
    )
    emails_form.add_email_button = has_smtp
    emails_form.render_field_macro_file = "core/partial/emails_field.html"
    return emails_form


def profile_edition_add_email(user, edited_user, emails_form):
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
    return send_confirmation_email(emails_form.new_email.data, email_confirmation_url)


def profile_edition_remove_email(user, edited_user, email):
    if email not in edited_user.emails:
        return False

    if len(edited_user.emails) == 1:
        return False

    edited_user.emails = [m for m in edited_user.emails if m != email]
    Backend.instance.save(edited_user)
    return True


@bp.route("/profile/<user:edited_user>", methods=("GET", "POST"))
@user_needed()
def profile_edition(user, edited_user):
    if not user.can_manage_users and not (
        user.can_edit_self and edited_user.id == user.id
    ):
        abort(404)

    request_ip = request.remote_addr or "unknown IP"
    menuitem = "profile" if edited_user.id == user.id else "users"
    emails_readonly = (
        current_app.features.has_email_confirmation and not user.can_manage_users
    )

    profile_form = profile_edition_main_form(user, edited_user, emails_readonly)
    emails_form = (
        profile_edition_emails_form(user, edited_user, current_app.features.has_smtp)
        if emails_readonly
        else None
    )

    has_email_changed = "emails" in profile_form and set(
        profile_form["emails"].data
    ) != set(user.emails)

    render_context = {
        "menuitem": menuitem,
        "edited_user": edited_user,
        "profile_form": profile_form,
        "emails_form": emails_form,
    }

    if not request.form or profile_form.form_control():
        return render_template("core/profile_edit.html", **render_context)

    if request.form.get("action") == "edit-profile" or (
        request_is_partial() and request.headers.get("HX-Trigger-Name") in profile_form
    ):
        if not profile_form.validate():
            flash(_("Profile edition failed."), "error")
            return render_template("core/profile_edit.html", **render_context)

        profile_edition_main_form_validation(user, edited_user, profile_form)

        if has_email_changed:
            current_app.logger.security(
                f"Updated email for {edited_user.user_name} from {request_ip}"
            )

        flash(_("Profile updated successfully."), "success")

        return redirect(
            url_for("core.account.profile_edition", edited_user=edited_user)
        )

    if request.form.get("action") == "add_email" or (
        request_is_partial() and request.headers.get("HX-Trigger-Name") in emails_form
    ):
        if not emails_form.validate():
            flash(_("Email addition failed."), "error")
            return render_template("core/profile_edit.html", **render_context)

        if profile_edition_add_email(user, edited_user, emails_form):
            flash(
                _(
                    "An email has been sent to the email address. "
                    "Please check your inbox and click on the verification link it contains"
                ),
                "success",
            )
        else:
            flash(_("Could not send the verification email"), "error")

        return redirect(
            url_for("core.account.profile_edition", edited_user=edited_user)
        )

    if request.form.get("email_remove"):
        if not profile_edition_remove_email(
            user, edited_user, request.form.get("email_remove")
        ):
            flash(_("Email deletion failed."), "error")
            return render_template("core/profile_edit.html", **render_context)

        flash(_("The email have been successfully deleted."), "success")
        return redirect(
            url_for("core.account.profile_edition", edited_user=edited_user)
        )

    abort(400, f"bad form action: {request.form.get('action')}")


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
        return profile_settings_edit(user, edited_user)

    if request.form.get("action") == "confirm-delete":
        return render_template(
            "core/modals/delete-account.html", edited_user=edited_user
        )

    if request.form.get("action") == "delete":
        return profile_delete(user, edited_user)

    if request.form.get("action") == "password-initialization-mail":
        statuses = [
            send_password_initialization_mail(edited_user, email)
            for email in edited_user.emails
        ]
        success = all(statuses)
        if success:
            flash(
                _(
                    "A password initialization link has been sent at the user email address. "
                    "It should be received within a few minutes."
                ),
                "success",
            )
        else:
            flash(_("Could not send the password initialization email"), "error")

        return profile_settings_edit(user, edited_user)

    if request.form.get("action") == "password-reset-mail":
        statuses = [
            send_password_reset_mail(edited_user, email) for email in edited_user.emails
        ]
        success = all(statuses)
        if success:
            flash(
                _(
                    "A password reset link has been sent at the user email address. "
                    "It should be received within a few minutes."
                ),
                "success",
            )
        else:
            flash(_("Could not send the password reset email"), "error")

        return profile_settings_edit(user, edited_user)

    if (
        request.form.get("action") == "confirm-lock"
        and current_app.features.has_account_lockability
        and not edited_user.locked
    ):
        return render_template("core/modals/lock-account.html", edited_user=edited_user)

    if (
        request.form.get("action") == "lock"
        and current_app.features.has_account_lockability
        and not edited_user.locked
    ):
        flash(_("The account has been locked"), "success")
        edited_user.lock_date = datetime.datetime.now(datetime.timezone.utc)
        Backend.instance.save(edited_user)

        return profile_settings_edit(user, edited_user)

    if (
        request.form.get("action") == "unlock"
        and current_app.features.has_account_lockability
        and edited_user.locked
    ):
        flash(_("The account has been unlocked"), "success")
        edited_user.lock_date = None
        Backend.instance.save(edited_user)

        return profile_settings_edit(user, edited_user)

    if (
        request.form.get("action") == "confirm-reset-otp"
        and current_app.features.has_otp
    ):
        return render_template("core/modals/reset-otp.html", edited_user=edited_user)

    if request.form.get("action") == "reset-otp" and current_app.features.has_otp:
        flash(_("One-time password authentication has been reset"), "success")
        request_ip = request.remote_addr or "unknown IP"
        current_app.logger.security(
            f"Reset one-time password authentication for {edited_user.user_name} by {user.user_name} from {request_ip}"
        )
        edited_user.initialize_otp()
        Backend.instance.save(edited_user)

        return profile_settings_edit(user, edited_user)

    abort(400, f"bad form action: {request.form.get('action')}")


def profile_settings_edit(editor, edited_user):
    menuitem = "profile" if editor.id == editor.id else "users"
    fields = editor.readable_fields | editor.writable_fields
    request_ip = request.remote_addr or "unknown IP"

    available_fields = {"password", "groups", "user_name", "lock_date"}
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
            flash(_("Profile edition failed."), "error")

        else:
            for attribute in form:
                if attribute.name in available_fields & editor.writable_fields:
                    setattr(edited_user, attribute.name, attribute.data)

            if (
                "password1" in request.form
                and form["password1"].data
                and request.form["action"] == "edit-settings"
            ):
                Backend.instance.set_user_password(edited_user, form["password1"].data)
                current_app.logger.security(
                    f"Changed password in settings for {edited_user.user_name} from {request_ip}"
                )

            Backend.instance.save(edited_user)
            flash(_("Profile updated successfully."), "success")
            return redirect(
                url_for("core.account.profile_settings", edited_user=edited_user)
            )

    return render_template(
        "core/profile_settings.html",
        form=form,
        menuitem=menuitem,
        edited_user=edited_user,
        self_deletion=edited_user.can_delete_account,
    )


def profile_delete(user, edited_user):
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

    if self_deletion:
        return redirect(url_for("core.account.index"))
    return redirect(url_for("core.account.users"))


@bp.route("/impersonate/<user:puppet>")
@user_needed("impersonate_users")
def impersonate(user, puppet):
    if puppet.locked:
        abort(403, _("Locked users cannot be impersonated."))

    login_user(puppet)
    flash(
        _("Connection successful. Welcome %(user)s", user=puppet.formatted_name),
        "success",
    )
    return redirect(url_for("core.account.index"))


@bp.route("/profile/<user:user>/<field>")
def photo(user, field):
    if field.lower() != "photo":
        abort(404)

    etag = None
    if request.if_modified_since and request.if_modified_since >= user.last_modified:
        return "", 304

    etag = build_hash(user.identifier, user.last_modified.isoformat())
    if request.if_none_match and etag in request.if_none_match:
        return "", 304

    photo = getattr(user, field)
    if not photo:
        abort(404)

    stream = io.BytesIO(photo)
    return send_file(
        stream, mimetype="image/jpeg", last_modified=user.last_modified, etag=etag
    )


@bp.route("/reset/<user:user>", methods=["GET", "POST"])
def reset(user):
    form = PasswordResetForm(request.form)
    if user != current_user() or not user.has_expired_password():
        abort(403)

    if request.form and form.validate():
        Backend.instance.set_user_password(user, form.password.data)
        login_user(user)
        flash(_("Your password has been updated successfully"), "success")
        return redirect(
            session.pop(
                "redirect-after-login",
                url_for("core.account.profile_edition", edited_user=user),
            )
        )

    return render_template("core/reset-password.html", form=form, user=user, hash=None)
