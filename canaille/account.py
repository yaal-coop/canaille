import hashlib
import pkg_resources

from flask import (
    Blueprint,
    request,
    flash,
    url_for,
    current_app,
    abort,
    render_template,
    redirect,
)
from flask_babel import gettext as _

from .forms import (
    LoginForm,
    ProfileForm,
    PasswordResetForm,
    ForgottenPasswordForm,
)
from .apputils import base64logo, send_email
from .flaskutils import current_user, user_needed, moderator_needed
from .models import User


bp = Blueprint(__name__, "home")


@bp.route("/")
def index():
    if not current_user():
        return redirect(url_for("canaille.account.login"))
    return redirect(
        url_for("canaille.account.profile_edition", username=current_user().uid[0])
    )


@bp.route("/about")
def about():
    try:
        version = pkg_resources.get_distribution("canaille").version
    except pkg_resources.DistributionNotFound:
        version = "git"
    return render_template("about.html", version=version)


@bp.route("/login", methods=("GET", "POST"))
def login():
    form = LoginForm(request.form or None)

    if request.form:
        user = User.get(form.login.data)
        if user and not user.has_password():
            return redirect(url_for("canaille.account.firstlogin", uid=user.uid[0]))

        if not form.validate() or not User.authenticate(
            form.login.data, form.password.data, True
        ):
            flash(_("Login failed, please check your information"), "error")
            return render_template("login.html", form=form)

        flash(_("Connection successful. Welcome %(user)s", user=user.name), "success")
        return redirect(url_for("canaille.account.index"))

    return render_template("login.html", form=form)


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
    user and not user.has_password() or abort(404)

    form = ForgottenPasswordForm(request.form or None, data={"login": uid})
    if not request.form:
        return render_template("firstlogin.html", form=form, uid=uid)

    if not form.validate():
        flash(_("Could not send the password initialization link."), "error")
        return render_template("firstlogin.html", form=form, uid=uid)

    base_url = url_for("canaille.account.index", _external=True)
    reset_url = url_for(
        "canaille.account.reset",
        uid=user.uid[0],
        hash=profile_hash(
            user.uid[0], user.userPassword[0] if user.has_password() else ""
        ),
        _external=True,
    )
    logo, logo_extension = base64logo()

    subject = _("Password initialization on {website_name}").format(
        website_name=current_app.config.get("NAME", reset_url)
    )
    text_body = render_template(
        "mail/firstlogin.txt",
        site_name=current_app.config.get("NAME", reset_url),
        site_url=base_url,
        reset_url=reset_url,
    )
    html_body = render_template(
        "mail/firstlogin.html",
        site_name=current_app.config.get("NAME", reset_url),
        site_url=base_url,
        reset_url=reset_url,
        logo=logo,
        logo_extension=logo_extension,
    )

    success = send_email(
        subject=subject,
        sender=current_app.config["SMTP"]["FROM_ADDR"],
        recipient=user.mail,
        text=text_body,
        html=html_body,
    )

    if success:
        flash(
            _(
                "A password initialization link has been sent at your email address. You should receive it within 10 minutes."
            ),
            "success",
        )
    else:
        flash(_("Could not send the password initialization email"), "error")

    return render_template("firstlogin.html", form=form, uid=uid)


@bp.route("/users")
@moderator_needed()
def users(user):
    users = User.filter(objectClass=current_app.config["LDAP"]["USER_CLASS"])
    return render_template("users.html", users=users, menuitem="users")


@bp.route("/profile", methods=("GET", "POST"))
@moderator_needed()
def profile_creation(user):
    claims = current_app.config["JWT"]["MAPPING"]
    form = ProfileForm(request.form or None)
    try:
        del form.sub.render_kw["readonly"]
    except KeyError:
        pass

    if request.form:
        if not form.validate():
            flash(_("User creation failed."), "error")

        else:
            user = User(objectClass=current_app.config["LDAP"]["USER_CLASS"])
            for attribute in form:
                model_attribute_name = claims.get(attribute.name.upper())
                if (
                    not model_attribute_name
                    or model_attribute_name not in user.must + user.may
                ):
                    continue

                user[model_attribute_name] = [attribute.data]

            user.cn = [f"{user.givenName[0]} {user.sn[0]}"]
            user.save()

            flash(_("User creation succeed."), "success")

            return redirect(
                url_for("canaille.account.profile_edition", username=user.uid[0])
            )

    return render_template(
        "profile.html", form=form, menuitem="users", edited_user=None
    )


@bp.route("/profile/<username>", methods=("GET", "POST"))
@user_needed()
def profile_edition(user, username):
    user.moderator or username == user.uid[0] or abort(403)

    if request.method == "GET" or request.form.get("action") == "edit":
        return profile_edit(user, username)

    if request.form.get("action") == "delete":
        return profile_delete(user, username)

    abort(400)


def profile_edit(user, username):
    menuitem = "profile" if username == user.uid[0] else "users"
    claims = current_app.config["JWT"]["MAPPING"]
    if username != user.uid[0]:
        user = User.get(username) or abort(404)

    data = {
        k.lower(): getattr(user, v)[0]
        if getattr(user, v) and isinstance(getattr(user, v), list)
        else getattr(user, v) or ""
        for k, v in claims.items()
    }
    form = ProfileForm(request.form or None, data=data)
    form.sub.render_kw["readonly"] = "true"

    if request.form:
        if not form.validate():
            flash(_("Profile edition failed."), "error")

        else:
            for attribute in form:
                model_attribute_name = claims.get(attribute.name.upper())
                if (
                    not model_attribute_name
                    or model_attribute_name not in user.must + user.may
                ):
                    continue

                user[model_attribute_name] = [attribute.data]

            if not form.password1.data or user.set_password(form.password1.data):
                flash(_("Profile updated successfuly."), "success")

            user.save()

    return render_template(
        "profile.html", form=form, menuitem=menuitem, edited_user=user
    )


def profile_delete(user, username):
    self_deletion = username == user.uid[0]
    if self_deletion:
        user.logout()
    else:
        user = User.get(username) or abort(404)

    flash(_("The user %(user)s has been sucessfuly deleted", user=user.name), "success")
    user.delete()

    if self_deletion:
        return redirect(url_for("canaille.account.index"))
    return redirect(url_for("canaille.account.users"))


def profile_hash(user, password):
    return hashlib.sha256(
        current_app.config["SECRET_KEY"].encode("utf-8")
        + user.encode("utf-8")
        + password.encode("utf-8")
    ).hexdigest()


@bp.route("/reset", methods=["GET", "POST"])
def forgotten():
    form = ForgottenPasswordForm(request.form)
    if not request.form:
        return render_template("forgotten-password.html", form=form)

    if not form.validate():
        flash(_("Could not send the password reset link."), "error")
        return render_template("forgotten-password.html", form=form)

    user = User.get(form.login.data)

    if not user:
        flash(
            _(
                "A password reset link has been sent at your email address. You should receive it within 10 minutes."
            ),
            "success",
        )
        return render_template("forgotten-password.html", form=form)

    base_url = url_for("canaille.account.index", _external=True)
    reset_url = url_for(
        "canaille.account.reset",
        uid=user.uid[0],
        hash=profile_hash(
            user.uid[0], user.userPassword[0] if user.has_password() else ""
        ),
        _external=True,
    )
    logo, logo_extension = base64logo()

    subject = _("Password reset on {website_name}").format(
        website_name=current_app.config.get("NAME", reset_url)
    )
    text_body = render_template(
        "mail/reset.txt",
        site_name=current_app.config.get("NAME", reset_url),
        site_url=base_url,
        reset_url=reset_url,
    )
    html_body = render_template(
        "mail/reset.html",
        site_name=current_app.config.get("NAME", reset_url),
        site_url=base_url,
        reset_url=reset_url,
        logo=logo,
        logo_extension=logo_extension,
    )

    success = send_email(
        subject=subject,
        sender=current_app.config["SMTP"]["FROM_ADDR"],
        recipient=user.mail,
        text=text_body,
        html=html_body,
    )

    if success:
        flash(
            _(
                "A password reset link has been sent at your email address. You should receive it within 10 minutes."
            ),
            "success",
        )
    else:
        flash(_("Could not reset your password"), "error")

    return render_template("forgotten-password.html", form=form)


@bp.route("/reset/<uid>/<hash>", methods=["GET", "POST"])
def reset(uid, hash):
    form = PasswordResetForm(request.form)
    user = User.get(uid)

    if not user or hash != profile_hash(
        user.uid[0], user.userPassword[0] if user.has_password() else ""
    ):
        flash(
            _("The password reset link that brought you here was invalid."),
            "error",
        )
        return redirect(url_for("canaille.account.index"))

    if request.form and form.validate():
        user.set_password(form.password.data)
        user.login()

        flash(_("Your password has been updated successfuly"), "success")
        return redirect(url_for("canaille.account.profile_edition", username=uid))

    return render_template("reset-password.html", form=form, uid=uid, hash=hash)
