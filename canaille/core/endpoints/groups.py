import binascii
import datetime

from flask import Blueprint
from flask import abort
from flask import current_app
from flask import flash
from flask import g
from flask import redirect
from flask import request
from flask import session
from flask import url_for

from canaille.app import b64_to_obj
from canaille.app import models
from canaille.app.flask import render_htmx_template
from canaille.app.flask import smtp_needed
from canaille.app.flask import user_needed
from canaille.app.forms import TableForm
from canaille.app.i18n import gettext as _
from canaille.app.templating import render_template
from canaille.backends import Backend
from canaille.core.endpoints.account import GroupInvitationPayload
from canaille.core.mails import send_group_invitation_mail

from .forms import CreateGroupForm
from .forms import DeleteGroupMemberForm
from .forms import EditGroupForm
from .forms import GroupInvitationForm

bp = Blueprint("groups", __name__, url_prefix="/groups")


@bp.route("/", methods=["GET", "POST"])
@user_needed()
def groups(user):
    if not (user.can("manage_groups") or user.can("create_groups")):
        abort(403)

    if request.form.get("action") == "confirm-leave":
        group_id = request.form.get("group_id")
        if not group_id:
            abort(400)

        group = Backend.instance.get(models.Group, id=group_id)
        if not group:
            abort(404)

        if user not in group.members:
            flash(_("You are not a member of this group."), "error")
            return redirect(url_for("core.groups.groups"))

        return render_template("core/modals/leave-group.html", group=group)

    filter = {"members": user} if not user.can("manage_groups") else {}
    table_form = TableForm(models.Group, formdata=request.form, filter=filter)
    if request.form and request.form.get("page") and not table_form.validate():
        abort(404)

    return render_htmx_template(
        "core/groups.html", menuitem="groups", table_form=table_form, user=user
    )


@bp.route("/add", methods=("GET", "POST"))
@user_needed()
def create_group(user):
    if not (user.can("manage_groups") or user.can("create_groups")):
        abort(403)
    form = CreateGroupForm(request.form or None)

    if request.form:
        if not form.validate():
            flash(_("Group creation failed."), "error")
        else:
            group = models.Group()
            group.members = [user]
            group.owner = user
            group.display_name = form.display_name.data
            group.description = form.description.data
            Backend.instance.save(group)
            flash(
                _(
                    "The group %(group)s has been successfully created",
                    group=group.display_name,
                ),
                "success",
            )
            return redirect(url_for("core.groups.group", group=group))

    return render_template(
        "core/group.html", menuitem="groups", form=form, edited_group=None, members=None
    )


def user_can_access_group(user, group):
    """Check if user can access group management."""
    return user.can("manage_groups") or group.user_can_edit(user)


@bp.route("/<group:group>", methods=("GET", "POST"))
@user_needed()
def group(user, group):
    if not user_can_access_group(user, group):
        abort(403)
    if (
        request.method == "GET"
        or request.form.get("action") == "edit"
        or request.form.get("page")
    ):
        return edit_group(group)

    if request.form.get("action") == "confirm-delete":
        return render_template("core/modals/delete-group.html", group=group)

    if request.form.get("action") == "delete":
        return delete_group(group)

    if request.form.get("action") == "confirm-remove-member":
        return delete_member(group)

    if request.form.get("action") == "remove-member":
        return delete_member(group)

    abort(400, f"bad form action: {request.form.get('action')}")


def edit_group(group):
    table_form = TableForm(models.User, filter={"groups": group}, formdata=request.form)
    if request.form and request.form.get("page") and not table_form.validate():
        abort(404)

    form = EditGroupForm(
        request.form or None,
        data={
            "display_name": group.display_name,
            "description": group.description or "",
        },
    )

    if (
        request.form
        and request.form.get("action") == "edit"
        and not request.form.get("page")
    ):
        if form.validate():
            group.description = form.description.data
            Backend.instance.save(group)
            flash(
                _(
                    "The group %(group)s has been successfully edited.",
                    group=group.display_name,
                ),
                "success",
            )
            return redirect(url_for("core.groups.group", group=group))
        else:
            flash(_("Group edition failed."), "error")

    return render_htmx_template(
        "core/group.html",
        "core/partial/group-members.html",
        form=form,
        menuitem="groups",
        edited_group=group,
        table_form=table_form,
    )


def delete_member(group):
    form = DeleteGroupMemberForm(request.form or None)
    form.group = group

    if not form.validate():
        flash(
            "\n".join(form.errors.get("member")),
            "error",
        )

    elif request.form.get("action") == "confirm-remove-member":
        return render_template(
            "core/modals/remove-group-member.html", group=group, form=form
        )

    else:
        flash(
            _(
                "%(user_name)s has been removed from the group %(group_name)s",
                user_name=form.member.data.formatted_name,
                group_name=group.display_name,
            ),
            "success",
        )
        group.members = [
            member for member in group.members if member != form.member.data
        ]
        Backend.instance.save(group)

    return edit_group(group)


def delete_group(group):
    flash(
        _(
            "The group %(group)s has been successfully deleted",
            group=group.display_name,
        ),
        "success",
    )
    Backend.instance.delete(group)
    return redirect(url_for("core.groups.groups"))


@bp.route("/<group:group>/leave", methods=["POST"])
@user_needed()
def leave_group(user, group):
    """Allow a user to leave a group and remove ownership if they are the owner."""
    if user not in group.members:
        flash(_("You are not a member of this group."), "error")
        return redirect(url_for("core.account.index"))

    group.members = [member for member in group.members if member != user]

    if user == group.owner:
        group.owner = None

    Backend.instance.save(group)

    flash(_("You have left %(group)s.", group=group.display_name), "success")
    return redirect(url_for("core.groups.groups"))


@bp.route("/<group:group>/invite", methods=["GET", "POST"])
@smtp_needed()
@user_needed()
def invite_to_group(user, group):
    """Send an invitation email to a user to join a group."""
    if not user_can_access_group(user, group):
        abort(403)

    form = GroupInvitationForm(request.form or None)
    email_sent = False
    form_validated = False
    invitation_url = None

    if request.form and form.validate():
        form_validated = True
        existing_users = Backend.instance.query(models.User, emails=form.email.data)
        if not existing_users:
            flash(_("No user found with this email address."), "error")
            return render_template(
                "core/invite_group_member.html",
                form=form,
                group=group,
                menuitem="groups",
                form_validated=False,
                email_sent=False,
                invitation_url=None,
            )

        invited_user = existing_users[0]
        if invited_user in group.members:
            flash(
                _("A user with this email address is already a member of this group."),
                "error",
            )
            return render_template(
                "core/invite_group_member.html",
                form=form,
                group=group,
                menuitem="groups",
                form_validated=False,
                email_sent=False,
                invitation_url=None,
            )

        expiration_date = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(
            seconds=current_app.config["CANAILLE"]["INVITATION_EXPIRATION"]
        )
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id=group.id,
            invited_user_id=invited_user.id,
        )

        invitation_url = url_for(
            "core.groups.join_group",
            data=payload.b64(),
            hash=payload.build_hash(),
            _external=True,
        )

        email_sent = send_group_invitation_mail(
            form.email.data,
            invitation_url,
            group.display_name,
            user.formatted_name,
        )

    return render_template(
        "core/invite_group_member.html",
        form=form,
        group=group,
        menuitem="groups",
        form_validated=form_validated,
        email_sent=email_sent,
        invitation_url=invitation_url,
    )


@bp.route("/join/<data>/<hash>", methods=["GET", "POST"])
def join_group(data, hash):
    """Handle group invitation link validation and add user to group."""
    try:
        payload = GroupInvitationPayload(*b64_to_obj(data))
    except (binascii.Error, TypeError):
        flash(_("The invitation link that brought you here was invalid."), "error")
        return redirect(url_for("core.account.index"))

    if not (group := Backend.instance.get(models.Group, id=payload.group_id)):
        flash(_("The group you were invited to no longer exists."), "error")
        return redirect(url_for("core.account.index"))

    if not (
        invited_user := Backend.instance.get(models.User, id=payload.invited_user_id)
    ):
        flash(_("The invitation link that brought you here was invalid."), "error")
        return redirect(url_for("core.account.index"))

    if not g.session or not g.session.user:
        flash(
            _(
                "You have been invited to join the group '%(group)s'. Please log in to accept the invitation.",
                group=group.display_name,
            ),
            "info",
        )
        session["redirect-after-login"] = request.url
        return redirect(url_for("core.auth.login", username=invited_user.user_name))

    if g.session.user.id != payload.invited_user_id:
        flash(_("This invitation was not sent to you."), "error")
        return redirect(url_for("core.account.index"))

    if payload.has_expired():
        flash(_("The invitation link that brought you here has expired."), "error")
        return redirect(url_for("core.account.index"))

    if hash != payload.build_hash():
        flash(_("The invitation link that brought you here was invalid."), "error")
        return redirect(url_for("core.account.index"))

    if g.session.user in group.members:
        flash(
            _("You are already a member of %(group)s.", group=group.display_name),
            "info",
        )
        return redirect(
            url_for("core.account.profile_settings", edited_user=g.session.user)
        )

    group.members = list(group.members) + [g.session.user]
    Backend.instance.save(group)

    flash(
        _("You have successfully joined %(group)s!", group=group.display_name),
        "success",
    )
    return redirect(
        url_for("core.account.profile_settings", edited_user=g.session.user)
    )
