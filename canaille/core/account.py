import datetime
import io
from dataclasses import astuple
from dataclasses import dataclass
from typing import List

import pkg_resources
import wtforms
from canaille.app import b64_to_obj
from canaille.app import default_fields
from canaille.app import models
from canaille.app import obj_to_b64
from canaille.app import profile_hash
from canaille.app.flask import current_user
from canaille.app.flask import permissions_needed
from canaille.app.flask import render_htmx_template
from canaille.app.flask import request_is_htmx
from canaille.app.flask import smtp_needed
from canaille.app.flask import user_needed
from canaille.app.forms import TableForm
from canaille.backends import BaseBackend
from flask import abort
from flask import Blueprint
from flask import current_app
from flask import flash
from flask import redirect
from flask import request
from flask import send_file
from flask import session
from flask import url_for
from flask_babel import gettext as _
from flask_babel import refresh
from flask_themer import render_template
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.datastructures import FileStorage

from .forms import FirstLoginForm
from .forms import ForgottenPasswordForm
from .forms import InvitationForm
from .forms import LoginForm
from .forms import MINIMUM_PASSWORD_LENGTH
from .forms import PasswordForm
from .forms import PasswordResetForm
from .forms import profile_form
from .forms import PROFILE_FORM_FIELDS
from .mails import send_invitation_mail
from .mails import send_password_initialization_mail
from .mails import send_password_reset_mail


bp = Blueprint("account", __name__)


@bp.route("/")
def index():
    user = current_user()

    if not user:
        return redirect(url_for("account.login"))

    if user.can_edit_self or user.can_manage_users:
        return redirect(url_for("account.profile_edition", edited_user=user))

    if user.can_use_oidc:
        return redirect(url_for("oidc.consents.consents"))

    return redirect(url_for("account.about"))


@bp.route("/about")
def about():
    try:
        version = pkg_resources.get_distribution("canaille").version
    except pkg_resources.DistributionNotFound:  # pragma: no cover
        version = "git"
    return render_template("about.html", version=version)


@bp.route("/login", methods=("GET", "POST"))
def login():
    if current_user():
        return redirect(url_for("account.profile_edition", edited_user=current_user()))

    form = LoginForm(request.form or None)
    form.render_field_macro_file = "partial/login_field.html"
    form["login"].render_kw["placeholder"] = BaseBackend.get().login_placeholder()

    if not request.form or form.form_control():
        return render_template("login.html", form=form)

    user = models.User.get_from_login(form.login.data)
    if user and not user.has_password():
        return redirect(url_for("account.firstlogin", user=user))

    if not form.validate():
        models.User.logout()
        flash(_("Login failed, please check your information"), "error")
        return render_template("login.html", form=form)

    session["attempt_login"] = form.login.data
    return redirect(url_for("account.password"))


@bp.route("/password", methods=("GET", "POST"))
def password():
    if "attempt_login" not in session:
        return redirect(url_for("account.login"))

    form = PasswordForm(request.form or None)
    form.render_field_macro_file = "partial/login_field.html"

    if not request.form or form.form_control():
        return render_template(
            "password.html", form=form, username=session["attempt_login"]
        )

    user = models.User.get_from_login(session["attempt_login"])
    if user and not user.has_password():
        return redirect(url_for("account.firstlogin", user=user))

    if not form.validate() or not user:
        models.User.logout()
        flash(_("Login failed, please check your information"), "error")
        return render_template(
            "password.html", form=form, username=session["attempt_login"]
        )

    success, message = user.check_password(form.password.data)
    if not success:
        models.User.logout()
        flash(message or _("Login failed, please check your information"), "error")
        return render_template(
            "password.html", form=form, username=session["attempt_login"]
        )

    del session["attempt_login"]
    user.login()
    flash(
        _("Connection successful. Welcome %(user)s", user=user.formatted_name[0]),
        "success",
    )
    return redirect(url_for("account.index"))


@bp.route("/logout")
def logout():
    user = current_user()

    if user:
        flash(
            _(
                "You have been disconnected. See you next time %(user)s",
                user=user.formatted_name[0],
            ),
            "success",
        )
        user.logout()
    return redirect("/")


@bp.route("/firstlogin/<user:user>", methods=("GET", "POST"))
def firstlogin(user):
    if user.has_password():
        abort(404)

    form = FirstLoginForm(request.form or None)
    if not request.form:
        return render_template("firstlogin.html", form=form, user=user)

    form.validate()

    success = all(
        send_password_initialization_mail(user, email) for email in user.emails
    )
    if success:
        flash(
            _(
                "A password initialization link has been sent at your email address. "
                "You should receive it within a few minutes."
            ),
            "success",
        )
    else:
        flash(_("Could not send the password initialization email"), "error")

    return render_template("firstlogin.html", form=form)


@bp.route("/users", methods=["GET", "POST"])
@permissions_needed("manage_users")
def users(user):
    table_form = TableForm(
        models.User, fields=user.read | user.write, formdata=request.form
    )
    if request.form and not table_form.validate():
        abort(404)

    return render_htmx_template(
        "users.html",
        menuitem="users",
        table_form=table_form,
    )


@dataclass
class Invitation:
    creation_date_isoformat: str
    user_name: str
    user_name_editable: bool
    email: str
    groups: List[str]

    @property
    def creation_date(self):
        return datetime.datetime.fromisoformat(self.creation_date_isoformat)

    def has_expired(self):
        DEFAULT_INVITATION_DURATION = 2 * 24 * 60 * 60
        return datetime.datetime.now(
            datetime.timezone.utc
        ) - self.creation_date > datetime.timedelta(
            seconds=current_app.config.get(
                "INVITATION_EXPIRATION", DEFAULT_INVITATION_DURATION
            )
        )

    def b64(self):
        return obj_to_b64(astuple(self))

    def profile_hash(self):
        return profile_hash(*astuple(self))


@bp.route("/invite", methods=["GET", "POST"])
@smtp_needed()
@permissions_needed("manage_users")
def user_invitation(user):
    form = InvitationForm(request.form or None)

    email_sent = None
    registration_url = None
    form_validated = False
    if request.form and form.validate():
        form_validated = True
        invitation = Invitation(
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
            form.user_name.data,
            form.user_name_editable.data,
            form.email.data,
            form.groups.data,
        )
        registration_url = url_for(
            "account.registration",
            data=invitation.b64(),
            hash=invitation.profile_hash(),
            _external=True,
        )

        if request.form["action"] == "send":
            email_sent = send_invitation_mail(form.email.data, registration_url)

    return render_template(
        "invite.html",
        form=form,
        menuitems="users",
        form_validated=form_validated,
        email_sent=email_sent,
        registration_url=registration_url,
    )


@bp.route("/register/<data>/<hash>", methods=["GET", "POST"])
def registration(data, hash):
    try:
        invitation = Invitation(*b64_to_obj(data))
    except:
        flash(
            _("The invitation link that brought you here was invalid."),
            "error",
        )
        return redirect(url_for("account.index"))

    if invitation.has_expired():
        flash(
            _("The invitation link that brought you here has expired."),
            "error",
        )
        return redirect(url_for("account.index"))

    if models.User.get_from_login(invitation.user_name):
        flash(
            _("Your account has already been created."),
            "error",
        )
        return redirect(url_for("account.index"))

    if current_user():
        flash(
            _("You are already logged in, you cannot create an account."),
            "error",
        )
        return redirect(url_for("account.index"))

    if hash != invitation.profile_hash():
        flash(
            _("The invitation link that brought you here was invalid."),
            "error",
        )
        return redirect(url_for("account.index"))

    data = {
        "user_name": invitation.user_name,
        "emails": [invitation.email],
        "groups": invitation.groups,
    }

    readable_fields, writable_fields = default_fields()

    form = profile_form(writable_fields, readable_fields)
    if "groups" not in form and invitation.groups:
        form["groups"] = wtforms.SelectMultipleField(
            _("Groups"),
            choices=[(group.id, group.display_name) for group in models.Group.query()],
            render_kw={"readonly": "true"},
        )
    form.process(CombinedMultiDict((request.files, request.form)) or None, data=data)

    if "readonly" in form["user_name"].render_kw and invitation.user_name_editable:
        del form["user_name"].render_kw["readonly"]

    form["password1"].validators = [
        wtforms.validators.DataRequired(),
        wtforms.validators.Length(min=MINIMUM_PASSWORD_LENGTH),
    ]
    form["password2"].validators = [
        wtforms.validators.DataRequired(),
        wtforms.validators.Length(min=MINIMUM_PASSWORD_LENGTH),
    ]
    form["password1"].flags.required = True
    form["password2"].flags.required = True

    if not request.form or form.form_control():
        return render_template(
            "profile_add.html",
            form=form,
            menuitem="users",
            edited_user=None,
            self_deletion=False,
        )

    if not form.validate():
        flash(_("User account creation failed."), "error")
        return render_template(
            "profile_add.html",
            form=form,
            menuitem="users",
            edited_user=None,
            self_deletion=False,
        )

    user = profile_create(current_app, form)
    user.login()
    flash(_("Your account has been created successfully."), "success")
    return redirect(url_for("account.profile_edition", edited_user=user))


@bp.route("/profile", methods=("GET", "POST"))
@permissions_needed("manage_users")
def profile_creation(user):
    form = profile_form(user.write, user.read)
    form.process(CombinedMultiDict((request.files, request.form)) or None)

    for field in form:
        if field.render_kw and "readonly" in field.render_kw:
            del field.render_kw["readonly"]

    if not request.form or form.form_control():
        return render_template(
            "profile_add.html",
            form=form,
            menuitem="users",
            edited_user=None,
            self_deletion=False,
        )

    if not form.validate():
        flash(_("User account creation failed."), "error")
        return render_template(
            "profile_add.html",
            form=form,
            menuitem="users",
            edited_user=None,
            self_deletion=False,
        )

    user = profile_create(current_app, form)
    return redirect(url_for("account.profile_edition", edited_user=user))


def profile_create(current_app, form):
    user = models.User()
    for attribute in form:
        if attribute.name in user.attributes:
            if isinstance(attribute.data, FileStorage):
                data = attribute.data.stream.read()
            else:
                data = attribute.data

            setattr(user, attribute.name, data)

        if "photo" in form and form["photo_delete"].data:
            del user.photo

    given_name = user.given_name[0] if user.given_name else ""
    family_name = user.family_name[0] if user.family_name else ""
    user.formatted_name = [f"{given_name} {family_name}".strip()]
    user.save()

    if form["password1"].data:
        user.set_password(form["password1"].data)
        user.save()

    flash(_("User account creation succeed."), "success")

    return user


@bp.route("/profile/<user:edited_user>", methods=("GET", "POST"))
@user_needed()
def profile_edition(user, edited_user):
    if not user.can_manage_users and not (user.can_edit_self and edited_user == user):
        abort(404)

    menuitem = "profile" if edited_user == user else "users"
    fields = user.read | user.write

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
    data = {
        field: getattr(edited_user, field)[0]
        if getattr(edited_user, field)
        and isinstance(getattr(edited_user, field), list)
        and not PROFILE_FORM_FIELDS[field].field_class == wtforms.FieldList
        else getattr(edited_user, field) or ""
        for field in fields
        if hasattr(edited_user, field) and field in available_fields
    }

    form = profile_form(
        user.write & available_fields, user.read & available_fields, edited_user
    )
    form.process(CombinedMultiDict((request.files, request.form)) or None, data=data)
    form.render_field_macro_file = "partial/profile_field.html"
    form.render_field_extra_context = {
        "user": user,
        "edited_user": edited_user,
    }

    if not request.form or form.form_control():
        return render_template(
            "profile_edit.html",
            form=form,
            menuitem=menuitem,
            edited_user=edited_user,
        )

    if not form.validate():
        flash(_("Profile edition failed."), "error")
        return render_template(
            "profile_edit.html",
            form=form,
            menuitem=menuitem,
            edited_user=edited_user,
        )

    for attribute in form:
        if attribute.name in edited_user.attributes and attribute.name in user.write:
            if isinstance(attribute.data, FileStorage):
                data = attribute.data.stream.read()
            else:
                data = attribute.data

            setattr(edited_user, attribute.name, data)

    if "photo" in form and form["photo_delete"].data:
        del edited_user.photo

    if "preferred_language" in request.form:
        # Refresh the babel cache in case the lang is updated
        refresh()

        if form["preferred_language"].data == "auto":
            edited_user.preferred_language = None

    edited_user.save()
    flash(_("Profile updated successfully."), "success")
    return redirect(url_for("account.profile_edition", edited_user=edited_user))


@bp.route("/profile/<user:edited_user>/settings", methods=("GET", "POST"))
@user_needed()
def profile_settings(user, edited_user):
    if not user.can_manage_users and not (user.can_edit_self and edited_user == user):
        abort(404)

    if (
        request.method == "GET"
        or request.form.get("action") == "edit"
        or request_is_htmx()
    ):
        return profile_settings_edit(user, edited_user)

    if request.form.get("action") == "delete":
        return profile_delete(user, edited_user)

    if request.form.get("action") == "password-initialization-mail":
        success = all(
            send_password_initialization_mail(edited_user, email)
            for email in edited_user.emails
        )
        if success:
            flash(
                _(
                    "A password initialization link has been sent at the user email address. It should be received within a few minutes."
                ),
                "success",
            )
        else:
            flash(_("Could not send the password initialization email"), "error")

        return profile_settings_edit(user, edited_user)

    if request.form.get("action") == "password-reset-mail":
        success = all(
            send_password_reset_mail(edited_user, email) for email in edited_user.emails
        )
        if success:
            flash(
                _(
                    "A password reset link has been sent at the user email address. It should be received within a few minutes."
                ),
                "success",
            )
        else:
            flash(_("Could not send the password reset email"), "error")

        return profile_settings_edit(user, edited_user)

    if (
        request.form.get("action") == "lock"
        and BaseBackend.get().has_account_lockability()
        and not edited_user.locked
    ):
        flash(_("The account has been locked"), "success")
        edited_user.lock_date = datetime.datetime.now(datetime.timezone.utc)
        edited_user.save()

        return profile_settings_edit(user, edited_user)

    if (
        request.form.get("action") == "unlock"
        and BaseBackend.get().has_account_lockability()
        and edited_user.locked
    ):
        flash(_("The account has been unlocked"), "success")
        del edited_user.lock_date
        edited_user.save()

        return profile_settings_edit(user, edited_user)

    abort(400)


def profile_settings_edit(editor, edited_user):
    menuitem = "profile" if editor.id == editor.id else "users"
    fields = editor.read | editor.write

    available_fields = {"password", "groups", "user_name", "lock_date"}
    data = {
        k: getattr(edited_user, k)[0]
        if getattr(edited_user, k) and isinstance(getattr(edited_user, k), list)
        else getattr(edited_user, k) or ""
        for k in fields
        if hasattr(edited_user, k) and k in available_fields
    }

    if "groups" in fields:
        data["groups"] = [g.id for g in edited_user.groups]

    form = profile_form(
        editor.write & available_fields, editor.read & available_fields, edited_user
    )
    form.process(CombinedMultiDict((request.files, request.form)) or None, data=data)

    if request.form and request.form.get("action") == "edit" or request_is_htmx():
        if not form.validate():
            flash(_("Profile edition failed."), "error")

        else:
            for attribute in form:
                if attribute.name in available_fields & editor.write:
                    setattr(edited_user, attribute.name, attribute.data)

            if (
                "password1" in request.form
                and form["password1"].data
                and request.form["action"] == "edit"
            ):
                edited_user.set_password(form["password1"].data)

            edited_user.save()
            flash(_("Profile updated successfully."), "success")
            return redirect(
                url_for("account.profile_settings", edited_user=edited_user)
            )

    return render_template(
        "profile_settings.html",
        form=form,
        menuitem=menuitem,
        edited_user=edited_user,
        self_deletion=edited_user.can_delete_account,
    )


def profile_delete(user, edited_user):
    self_deletion = user.id == edited_user.id
    if self_deletion:
        user.logout()

    flash(
        _(
            "The user %(user)s has been sucessfuly deleted",
            user=edited_user.formatted_name[0],
        ),
        "success",
    )
    edited_user.delete()

    if self_deletion:
        return redirect(url_for("account.index"))
    return redirect(url_for("account.users"))


@bp.route("/impersonate/<user:puppet>")
@permissions_needed("impersonate_users")
def impersonate(user, puppet):
    puppet.login()
    flash(
        _("Connection successful. Welcome %(user)s", user=puppet.formatted_name),
        "success",
    )
    return redirect(url_for("account.index"))


@bp.route("/reset", methods=["GET", "POST"])
@smtp_needed()
def forgotten():
    if not current_app.config.get("ENABLE_PASSWORD_RECOVERY", True):
        abort(404)

    form = ForgottenPasswordForm(request.form)
    if not request.form:
        return render_template("forgotten-password.html", form=form)

    if not form.validate():
        flash(_("Could not send the password reset link."), "error")
        return render_template("forgotten-password.html", form=form)

    user = models.User.get_from_login(form.login.data)
    success_message = _(
        "A password reset link has been sent at your email address. You should receive it within a few minutes."
    )
    if current_app.config.get("HIDE_INVALID_LOGINS", True) and (
        not user or not user.can_edit_self
    ):
        flash(success_message, "success")
        return render_template("forgotten-password.html", form=form)

    if not user.can_edit_self:
        flash(
            _(
                "The user '%(user)s' does not have permissions to update their password. "
                "We cannot send a password reset email.",
                user=user.formatted_name[0],
            ),
            "error",
        )
        return render_template("forgotten-password.html", form=form)

    success = all(send_password_reset_mail(user, email) for email in user.emails)

    if success:
        flash(success_message, "success")
    else:
        flash(
            _("We encountered an issue while we sent the password recovery email."),
            "error",
        )

    return render_template("forgotten-password.html", form=form)


@bp.route("/reset/<user:user>/<hash>", methods=["GET", "POST"])
def reset(user, hash):
    if not current_app.config.get("ENABLE_PASSWORD_RECOVERY", True):
        abort(404)

    form = PasswordResetForm(request.form)
    hashes = {
        profile_hash(
            user.identifier,
            email,
            user.password[0] if user.has_password() else "",
        )
        for email in user.emails
    }
    if not user or hash not in hashes:
        flash(
            _("The password reset link that brought you here was invalid."),
            "error",
        )
        return redirect(url_for("account.index"))

    if request.form and form.validate():
        user.set_password(form.password.data)
        user.login()

        flash(_("Your password has been updated successfully"), "success")
        return redirect(url_for("account.profile_edition", edited_user=user))

    return render_template("reset-password.html", form=form, user=user, hash=hash)


@bp.route("/profile/<user:user>/<field>")
def photo(user, field):
    if field.lower() != "photo":
        abort(404)

    etag = None
    if request.if_modified_since and request.if_modified_since >= user.last_modified:
        return "", 304

    etag = profile_hash(user.identifier, user.last_modified.isoformat())
    if request.if_none_match and etag in request.if_none_match:
        return "", 304

    photos = getattr(user, field)
    if not photos:
        abort(404)

    stream = io.BytesIO(photos[0])
    return send_file(
        stream, mimetype="image/jpeg", last_modified=user.last_modified, etag=etag
    )
