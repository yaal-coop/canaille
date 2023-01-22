import io
from dataclasses import astuple
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from typing import List

import pkg_resources
import wtforms
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
from flask_themer import render_template
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.datastructures import FileStorage

from .apputils import b64_to_obj
from .apputils import default_fields
from .apputils import login_placeholder
from .apputils import obj_to_b64
from .apputils import profile_hash
from .flaskutils import current_user
from .flaskutils import permissions_needed
from .flaskutils import smtp_needed
from .flaskutils import user_needed
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
            url_for("account.profile_edition", username=current_user().uid[0])
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
            url_for("account.profile_edition", username=current_user().uid[0])
        )

    form = LoginForm(request.form or None)
    form["login"].render_kw["placeholder"] = login_placeholder()

    if request.form:
        user = User.get(form.login.data)
        if user and not user.has_password():
            return redirect(url_for("account.firstlogin", uid=user.uid[0]))

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
        user = User.get(session["attempt_login"])
        if user and not user.has_password():
            return redirect(url_for("account.firstlogin", uid=user.uid[0]))

        if not form.validate() or not User.authenticate(
            session["attempt_login"], form.password.data, True
        ):
            User.logout()
            flash(_("Login failed, please check your information"), "error")
            return render_template(
                "password.html", form=form, username=session["attempt_login"]
            )

        del session["attempt_login"]
        flash(_("Connection successful. Welcome %(user)s", user=user.name), "success")
        return redirect(url_for("account.index"))

    return render_template(
        "password.html", form=form, username=session["attempt_login"]
    )


@bp.route("/logout")
def logout():
    user = current_user()
    if user:
        flash(
            _("You have been disconnected. See you next time %(user)s", user=user.name),
            "success",
        )
        user.logout()
    return redirect("/")


@bp.route("/firstlogin/<uid>", methods=("GET", "POST"))
def firstlogin(uid):
    user = User.get(uid)
    if not user or user.has_password():
        abort(404)

    form = FirstLoginForm(request.form or None)
    if not request.form:
        return render_template("firstlogin.html", form=form, uid=uid)

    if not form.validate():
        flash(_("Could not send the password initialization link."), "error")
        return render_template("firstlogin.html", form=form, uid=uid)

    if send_password_initialization_mail(user):
        flash(
            _(
                "A password initialization link has been sent at your email address. You should receive it within a few minutes."
            ),
            "success",
        )
    else:
        flash(_("Could not send the password initialization email"), "error")

    return render_template("firstlogin.html", form=form, uid=uid)


@bp.route("/users")
@permissions_needed("manage_users")
def users(user):
    users = User.all()
    return render_template("users.html", users=users, menuitem="users")


@dataclass
class Invitation:
    creation_date_isoformat: str
    uid: str
    uid_editable: bool
    mail: str
    groups: List[str]

    @property
    def creation_date(self):
        return datetime.fromisoformat(self.creation_date_isoformat)

    def has_expired(self):
        DEFAULT_INVITATION_DURATION = 2 * 24 * 60 * 60
        return datetime.now() - self.creation_date > timedelta(
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

    mail_sent = None
    registration_url = None
    form_validated = False
    if request.form and form.validate():
        form_validated = True
        invitation = Invitation(
            datetime.now().isoformat(),
            form.uid.data,
            form.uid_editable.data,
            form.mail.data,
            form.groups.data,
        )
        registration_url = url_for(
            "account.registration",
            data=invitation.b64(),
            hash=invitation.profile_hash(),
            _external=True,
        )

        if request.form["action"] == "send":
            mail_sent = send_invitation_mail(form.mail.data, registration_url)

    return render_template(
        "invite.html",
        form=form,
        menuitems="users",
        form_validated=form_validated,
        mail_sent=mail_sent,
        registration_url=registration_url,
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
            return redirect(url_for("account.profile_edition", username=user.uid[0]))

    return render_template(
        "profile.html",
        form=form,
        menuitem="users",
        edited_user=None,
        self_deletion=False,
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

    if User.get(invitation.uid):
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

    data = {"uid": invitation.uid, "mail": invitation.mail, "groups": invitation.groups}

    readable_fields, writable_fields = default_fields()

    form = profile_form(writable_fields, readable_fields)
    if "groups" not in form and invitation.groups:
        form["groups"] = wtforms.SelectMultipleField(
            _("Groups"),
            choices=[(group.dn, group.name) for group in Group.all()],
            render_kw={"readonly": "true"},
        )
    form.process(CombinedMultiDict((request.files, request.form)) or None, data=data)

    if "readonly" in form["uid"].render_kw and invitation.uid_editable:
        del form["uid"].render_kw["readonly"]

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
            flash(_("You account has been created successfuly."), "success")
            return redirect(url_for("account.profile_edition", username=user.uid[0]))

    return render_template(
        "profile.html",
        form=form,
        menuitem="users",
        edited_user=None,
        self_deletion=False,
    )


def profile_create(current_app, form):
    user = User()
    for attribute in form:
        if attribute.name in user.may + user.must:
            if isinstance(attribute.data, FileStorage):
                data = attribute.data.stream.read()
            else:
                data = attribute.data

            user[attribute.name] = data

        if "jpegPhoto" in form and form["jpegPhoto_delete"].data:
            user["jpegPhoto"] = None

    user.cn = [f"{user.givenName[0]} {user.sn[0]}".strip()]
    user.save()

    if "groups" in form:
        groups = [Group.get(group_dn) for group_dn in form["groups"].data]
        for group in groups:
            group.add_member(user)

    if form["password1"].data:
        user.set_password(form["password1"].data)

    flash(_("User account creation succeed."), "success")
    user.save()

    return user


@bp.route("/profile/<username>", methods=("GET", "POST"))
@user_needed()
def profile_edition(user, username):
    if not user.can_manage_users and not (
        user.can_edit_self and username == user.uid[0]
    ):
        abort(403)

    if request.method == "GET" or request.form.get("action") == "edit":
        return profile_edit(user, username)

    if request.form.get("action") == "delete":
        return profile_delete(user, username)

    if request.form.get("action") == "password-initialization-mail":
        user = User.get(username)
        if not user:
            abort(404)

        if send_password_initialization_mail(user):
            flash(
                _(
                    "A password initialization link has been sent at the user email address. It should be received within a few minutes."
                ),
                "success",
            )
        else:
            flash(_("Could not send the password initialization email"), "error")

        return profile_edit(user, username)

    if request.form.get("action") == "password-reset-mail":
        user = User.get(username)
        if not user:
            abort(404)

        if send_password_reset_mail(user):
            flash(
                _(
                    "A password reset link has been sent at the user email address. It should be received within a few minutes."
                ),
                "success",
            )
        else:
            flash(_("Could not send the password reset email"), "error")

        return profile_edit(user, username)

    abort(400)


def profile_edit(editor, username):
    menuitem = "profile" if username == editor.uid[0] else "users"
    fields = editor.read | editor.write
    if username != editor.uid[0]:
        user = User.get(username)
    else:
        user = editor

    if not user:
        abort(404)

    data = {
        k: getattr(user, k)[0]
        if getattr(user, k) and isinstance(getattr(user, k), list)
        else getattr(user, k) or ""
        for k in fields
        if hasattr(user, k)
    }

    if "groups" in fields:
        data["groups"] = [g.dn for g in user.groups]

    form = profile_form(editor.write, editor.read)
    form.process(CombinedMultiDict((request.files, request.form)) or None, data=data)

    if request.form:
        if not form.validate():
            flash(_("Profile edition failed."), "error")

        else:
            for attribute in form:
                if (
                    attribute.name in user.may + user.must
                    and attribute.name in editor.write
                ):
                    if isinstance(attribute.data, FileStorage):
                        data = attribute.data.stream.read()
                    else:
                        data = attribute.data

                    user[attribute.name] = data

                elif attribute.name == "groups" and "groups" in editor.write:
                    user.set_groups(attribute.data)

            if "jpegPhoto" in form and form["jpegPhoto_delete"].data:
                user["jpegPhoto"] = None

            if (
                "password1" in request.form
                and form["password1"].data
                and request.form["action"] == "edit"
            ):
                user.set_password(form["password1"].data)

            if (
                "preferredLanguage" in request.form
                and form["preferredLanguage"].data == "auto"
            ):
                user.preferredLanguage = None

            flash(_("Profile updated successfuly."), "success")
            user.save()
            return redirect(url_for("account.profile_edition", username=username))

    return render_template(
        "profile.html",
        form=form,
        menuitem=menuitem,
        edited_user=user,
        self_deletion=user.can_delete_account,
    )


def profile_delete(user, username):
    self_deletion = username == user.uid[0]
    if self_deletion:
        user.logout()
    else:
        user = User.get(username)

    if not user:
        abort(404)

    flash(_("The user %(user)s has been sucessfuly deleted", user=user.name), "success")
    user.delete()

    if self_deletion:
        return redirect(url_for("account.index"))
    return redirect(url_for("account.users"))


@bp.route("/impersonate/<username>")
@permissions_needed("impersonate_users")
def impersonate(user, username):
    puppet = User.get(username)
    if not puppet:
        abort(404)

    puppet.login()
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

    user = User.get(form.login.data)
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
                user=user.name,
            ),
            "success",
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


@bp.route("/reset/<uid>/<hash>", methods=["GET", "POST"])
def reset(uid, hash):
    if not current_app.config.get("ENABLE_PASSWORD_RECOVERY", True):
        abort(404)

    form = PasswordResetForm(request.form)
    user = User.get(uid)

    if not user or hash != profile_hash(
        user.uid[0], user.mail[0], user.userPassword[0] if user.has_password() else ""
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
        return redirect(url_for("account.profile_edition", username=uid))

    return render_template("reset-password.html", form=form, uid=uid, hash=hash)


@bp.route("/profile/<uid>/<field>")
def photo(uid, field):
    if field.lower() != "jpegphoto":
        abort(404)

    user = User.get(uid)
    if not user:
        abort(404)

    photos = getattr(user, field)
    if not photos:
        abort(404)

    stream = io.BytesIO(photos[0])
    return send_file(stream, mimetype="image/jpeg")
