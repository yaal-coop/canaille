import datetime
import io
from dataclasses import astuple
from dataclasses import dataclass
from typing import List

import pkg_resources
import wtforms
from canaille.app import b64_to_obj
from canaille.app import default_fields
from canaille.app import login_placeholder
from canaille.app import obj_to_b64
from canaille.app import profile_hash
from canaille.app.flask import current_user
from canaille.app.flask import permissions_needed
from canaille.app.flask import render_htmx_template
from canaille.app.flask import request_is_htmx
from canaille.app.flask import smtp_needed
from canaille.app.flask import user_needed
from canaille.app.forms import TableForm
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
from .forms import PasswordForm
from .forms import PasswordResetForm
from .forms import profile_form
from .mails import send_invitation_mail
from .mails import send_password_initialization_mail
from .mails import send_password_reset_mail
from .models import Group
from .models import User


bp = Blueprint("account", __name__)


@bp.context_processor
def global_processor():
    return {
        "has_password_recovery": current_app.config.get(
            "ENABLE_PASSWORD_RECOVERY", True
        ),
    }


@bp.route("/")
def index():
    user = current_user()

    if not user:
        return redirect(url_for("account.login"))

    if user.can_edit_self or user.can_manage_users:
        return redirect(
            url_for("account.profile_edition", username=current_user().user_name[0])
        )

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
        return redirect(
            url_for("account.profile_edition", username=current_user().user_name[0])
        )

    form = LoginForm(request.form or None)
    form["login"].render_kw["placeholder"] = login_placeholder()

    if request.form:
        user = User.get_from_login(form.login.data)
        if user and not user.has_password():
            return redirect(url_for("account.firstlogin", user_name=user.user_name[0]))

        if not form.validate():
            User.logout()
            flash(_("Login failed, please check your information"), "error")
            return render_template("login.html", form=form)

        session["attempt_login"] = form.login.data
        return redirect(url_for("account.password"))

    return render_template("login.html", form=form)


@bp.route("/password", methods=("GET", "POST"))
def password():
    if "attempt_login" not in session:
        return redirect(url_for("account.login"))

    form = PasswordForm(request.form or None)

    if request.form:
        user = User.get_from_login(session["attempt_login"])
        if user and not user.has_password():
            return redirect(url_for("account.firstlogin", user_name=user.user_name[0]))

        if not form.validate() or not User.authenticate(
            session["attempt_login"], form.password.data, True
        ):
            User.logout()
            flash(_("Login failed, please check your information"), "error")
            return render_template(
                "password.html", form=form, username=session["attempt_login"]
            )

        del session["attempt_login"]
        flash(
            _("Connection successful. Welcome %(user)s", user=user.formatted_name[0]),
            "success",
        )
        return redirect(url_for("account.index"))

    return render_template(
        "password.html", form=form, username=session["attempt_login"]
    )


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


@bp.route("/firstlogin/<user_name>", methods=("GET", "POST"))
def firstlogin(user_name):
    user = User.get_from_login(user_name)
    if not user or user.has_password():
        abort(404)

    form = FirstLoginForm(request.form or None)
    if not request.form:
        return render_template("firstlogin.html", form=form, user_name=user_name)

    form.validate()

    if send_password_initialization_mail(user):
        flash(
            _(
                "A password initialization link has been sent at your email address. You should receive it within a few minutes."
            ),
            "success",
        )
    else:
        flash(_("Could not send the password initialization email"), "error")

    return render_template("firstlogin.html", form=form, user_name=user_name)


@bp.route("/users", methods=["GET", "POST"])
@permissions_needed("manage_users")
def users(user):
    table_form = TableForm(User, fields=user.read | user.write, formdata=request.form)
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

    if User.get_from_login(invitation.user_name):
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
        "email": invitation.email,
        "groups": invitation.groups,
    }

    readable_fields, writable_fields = default_fields()

    form = profile_form(writable_fields, readable_fields)
    if "groups" not in form and invitation.groups:
        form["groups"] = wtforms.SelectMultipleField(
            _("Groups"),
            choices=[(group.id, group.display_name) for group in Group.query()],
            render_kw={"readonly": "true"},
        )
    form.process(CombinedMultiDict((request.files, request.form)) or None, data=data)

    if "readonly" in form["user_name"].render_kw and invitation.user_name_editable:
        del form["user_name"].render_kw["readonly"]

    form["password1"].validators = [
        wtforms.validators.DataRequired(),
        wtforms.validators.Length(min=8),
    ]
    form["password2"].validators = [
        wtforms.validators.DataRequired(),
        wtforms.validators.Length(min=8),
    ]
    form["password1"].flags.required = True
    form["password2"].flags.required = True

    if request.form:
        if not form.validate():
            flash(_("User account creation failed."), "error")

        else:
            user = profile_create(current_app, form)
            user.login()
            flash(_("Your account has been created successfuly."), "success")
            return redirect(
                url_for("account.profile_edition", username=user.user_name[0])
            )

    return render_template(
        "profile_add.html",
        form=form,
        menuitem="users",
        edited_user=None,
        self_deletion=False,
    )


@bp.route("/profile", methods=("GET", "POST"))
@permissions_needed("manage_users")
def profile_creation(user):
    form = profile_form(user.write, user.read)
    form.process(CombinedMultiDict((request.files, request.form)) or None)

    for field in form:
        if field.render_kw and "readonly" in field.render_kw:
            del field.render_kw["readonly"]

    if request.form:
        if not form.validate():
            flash(_("User account creation failed."), "error")

        else:
            user = profile_create(current_app, form)
            return redirect(
                url_for("account.profile_edition", username=user.user_name[0])
            )

    return render_template(
        "profile_add.html",
        form=form,
        menuitem="users",
        edited_user=None,
        self_deletion=False,
    )


def profile_create(current_app, form):
    user = User()
    for attribute in form:
        if attribute.name in user.attribute_table:
            if isinstance(attribute.data, FileStorage):
                data = attribute.data.stream.read()
            else:
                data = attribute.data

            user[attribute.name] = data

        if "photo" in form and form["photo_delete"].data:
            user["photo"] = None

    user.formatted_name = [f"{user.given_name[0]} {user.family_name[0]}".strip()]
    user.save()

    if form["password1"].data:
        user.set_password(form["password1"].data)
        user.save()

    flash(_("User account creation succeed."), "success")

    return user


@bp.route("/profile/<username>", methods=("GET", "POST"))
@user_needed()
def profile_edition(user, username):
    editor = user
    if not user.can_manage_users and not (
        user.can_edit_self and username == user.user_name[0]
    ):
        abort(403)

    menuitem = "profile" if username == editor.user_name[0] else "users"
    fields = editor.read | editor.write
    if username != editor.user_name[0]:
        user = User.get_from_login(username)
    else:
        user = editor

    if not user:
        abort(404)

    available_fields = {
        "formatted_name",
        "title",
        "given_name",
        "family_name",
        "display_name",
        "email",
        "phone_number",
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
        k: getattr(user, k)[0]
        if getattr(user, k) and isinstance(getattr(user, k), list)
        else getattr(user, k) or ""
        for k in fields
        if hasattr(user, k) and k in available_fields
    }

    form = profile_form(
        editor.write & available_fields, editor.read & available_fields, user
    )
    form.process(CombinedMultiDict((request.files, request.form)) or None, data=data)

    if request.form:
        if not form.validate():
            flash(_("Profile edition failed."), "error")

        else:
            for attribute in form:
                if (
                    attribute.name in user.attribute_table
                    and attribute.name in editor.write
                ):
                    if isinstance(attribute.data, FileStorage):
                        data = attribute.data.stream.read()
                    else:
                        data = attribute.data

                    user[attribute.name] = data

            if "photo" in form and form["photo_delete"].data:
                user["photo"] = None

            if "preferred_language" in request.form:
                # Refresh the babel cache in case the lang is updated
                refresh()

                if form["preferred_language"].data == "auto":
                    user.preferred_language = None

            user.save()
            flash(_("Profile updated successfuly."), "success")
            return redirect(url_for("account.profile_edition", username=username))

    return render_template(
        "profile_edit.html",
        form=form,
        menuitem=menuitem,
        edited_user=user,
    )


@bp.route("/profile/<username>/settings", methods=("GET", "POST"))
@user_needed()
def profile_settings(user, username):
    if not user.can_manage_users and not (
        user.can_edit_self and username == user.user_name[0]
    ):
        abort(403)

    edited_user = User.get_from_login(username)
    if not edited_user:
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
        if send_password_initialization_mail(edited_user):
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
        if send_password_reset_mail(edited_user):
            flash(
                _(
                    "A password reset link has been sent at the user email address. It should be received within a few minutes."
                ),
                "success",
            )
        else:
            flash(_("Could not send the password reset email"), "error")

        return profile_settings_edit(user, edited_user)

    abort(400)


def profile_settings_edit(editor, edited_user):
    menuitem = "profile" if editor.id == editor.id else "users"
    fields = editor.read | editor.write

    available_fields = {"password", "groups", "user_name"}
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
                if attribute.name == "groups" and "groups" in editor.write:
                    edited_user.groups = attribute.data

            if (
                "password1" in request.form
                and form["password1"].data
                and request.form["action"] == "edit"
            ):
                edited_user.set_password(form["password1"].data)

            edited_user.save()
            flash(_("Profile updated successfuly."), "success")
            return redirect(
                url_for("account.profile_edition", username=edited_user.user_name[0])
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


@bp.route("/impersonate/<username>")
@permissions_needed("impersonate_users")
def impersonate(user, username):
    puppet = User.get_from_login(username)
    if not puppet:
        abort(404)

    puppet.login()

    flash(_("Connection successful. Welcome %(user)s", user=puppet.name), "success")
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

    user = User.get_from_login(form.login.data)
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

    success = send_password_reset_mail(user)

    if success:
        flash(success_message, "success")
    else:
        flash(
            _("We encountered an issue while we sent the password recovery email."),
            "error",
        )

    return render_template("forgotten-password.html", form=form)


@bp.route("/reset/<user_name>/<hash>", methods=["GET", "POST"])
def reset(user_name, hash):
    if not current_app.config.get("ENABLE_PASSWORD_RECOVERY", True):
        abort(404)

    form = PasswordResetForm(request.form)
    user = User.get_from_login(user_name)

    if not user or hash != profile_hash(
        user.user_name[0],
        user.email[0],
        user.password[0] if user.has_password() else "",
    ):
        flash(
            _("The password reset link that brought you here was invalid."),
            "error",
        )
        return redirect(url_for("account.index"))

    if request.form and form.validate():
        user.set_password(form.password.data)
        user.login()

        flash(_("Your password has been updated successfuly"), "success")
        return redirect(url_for("account.profile_edition", username=user_name))

    return render_template(
        "reset-password.html", form=form, user_name=user_name, hash=hash
    )


@bp.route("/profile/<user_name>/<field>")
def photo(user_name, field):
    if field.lower() != "photo":
        abort(404)

    user = User.get_from_login(user_name)
    if not user:
        abort(404)

    etag = None
    if request.if_modified_since and request.if_modified_since >= user.last_modified:
        return "", 304

    etag = profile_hash(user_name, user.last_modified.isoformat())
    if request.if_none_match and etag in request.if_none_match:
        return "", 304

    photos = getattr(user, field)
    if not photos:
        abort(404)

    stream = io.BytesIO(photos[0])
    return send_file(
        stream, mimetype="image/jpeg", last_modified=user.last_modified, etag=etag
    )
