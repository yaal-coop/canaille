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
from canaille.app.flask import request_is_partial
from canaille.app.flask import smtp_needed
from canaille.app.flask import user_needed
from canaille.app.forms import Form
from canaille.app.forms import TableForm
from canaille.app.i18n import gettext as _
from canaille.app.i18n import ngettext
from canaille.app.templating import render_template
from canaille.backends import Backend
from canaille.core.endpoints.account import GroupInvitationPayload
from canaille.core.mails import send_group_invitation_mail

from .forms import AddGroupMembersForm
from .forms import CreateGroupForm
from .forms import CreateGroupWithMembersForm
from .forms import DeleteGroupMemberForm
from .forms import EditGroupForm
from .forms import GroupInvitationForm

bp = Blueprint("groups", __name__, url_prefix="/groups")


@bp.route("/", methods=["GET", "POST"])
@user_needed()
def groups(user):
    if not (user.can("manage_all_groups") or user.can("manage_own_groups")):
        abort(403)

    form = Form(request.form or None)
    if form.action.data == "confirm-leave":
        group_id = request.form.get("group_id")
        if not group_id:
            abort(400)

        group = Backend.instance.get(models.Group, id=group_id)
        if not group:
            abort(404)

        if user not in group.members:
            flash(_("You are not a member of this group."), "error")
            return redirect(url_for("core.groups.groups"))

        return render_template("core/modals/leave-group.html", group=group, form=form)

    filter = {"members": user} if not user.can("manage_all_groups") else {}
    table_form = TableForm(models.Group, formdata=request.form, filter=filter)
    if request.form and request.form.get("page") and not table_form.validate():
        abort(404)

    return render_htmx_template(
        "core/groups.html",
        menuitem="groups",
        table_form=table_form,
        form=form,
        user=user,
    )


@bp.route("/add", methods=("GET", "POST"))
@user_needed()
def create_group(user):
    if not (user.can("manage_all_groups") or user.can("manage_own_groups")):
        abort(403)
    form_class = (
        CreateGroupWithMembersForm if user.can("manage_all_groups") else CreateGroupForm
    )
    form = form_class(request.form or None, group=None, data={"owners": [user]})

    if form.validate_on_submit():
        group = models.Group()
        group.owners = form.owners.data if "owners" in form else [user]
        group.members = list(
            dict.fromkeys([user, *(form.data.get("members") or []), *group.owners])
        )
        group.display_name = form.display_name.data
        group.description = form.description.data
        Backend.instance.save(group)
        flash(
            _(
                "The group %(group)s has been successfully created.",
                group=group.display_name,
            ),
            "success",
        )
        return redirect(url_for("core.groups.group", group=group))

    if request.form and not form.mutated:
        flash(
            _("The group couldn't be created. Please check the form and try again."),
            "error",
        )

    return render_template(
        "core/group.html", menuitem="groups", form=form, edited_group=None, members=None
    )


def user_can_access_group(user, group):
    """Check if user can access group management."""
    return user.can("manage_all_groups") or group.is_editable_by(user)


@bp.route("/<group:group>", methods=("GET", "POST"))
@user_needed()
def group(user, group):
    if not user_can_access_group(user, group):
        abort(403)

    form = EditGroupForm(
        request.form or None,
        group=group,
        editor=user,
        data={
            "display_name": group.display_name,
            "description": group.description or "",
            "owners": list(group.owners),
        },
    )
    action = form.action.data
    if (
        request.method == "GET"
        or action == "edit"
        or form.mutated
        or request.form.get("page")
        or request_is_partial()
    ):
        return edit_group(user, group, form)

    if action in ("confirm-delete", "delete") and not group.is_deletable_by(user):
        abort(403)

    if action == "confirm-delete":
        return render_template("core/modals/delete-group.html", group=group, form=form)

    if action == "delete":
        return delete_group(group)

    if action in ("confirm-remove-member", "remove-member"):
        return delete_member(user, group, form)

    if action in ("confirm-step-down", "step-down"):
        return step_down(user, group, form)

    abort(400, f"bad form action: {action}")


def edit_group(user, group, form):
    table_form = TableForm(models.User, filter={"groups": group}, formdata=request.form)
    if request.form and request.form.get("page") and not table_form.validate():
        abort(404)

    if (
        request.form
        and (form.action.data == "edit" or form.mutated)
        and not request.form.get("page")
    ):
        if form.validate_on_submit():
            group.description = form.description.data
            group.owners = form.owners.data
            Backend.instance.save(group)
            flash(
                _(
                    "The group %(group)s has been successfully edited.",
                    group=group.display_name,
                ),
                "success",
            )
            return redirect_after_ownership_change(user, group)

        if not form.mutated:
            flash(
                _(
                    "Your changes couldn't be saved. Please check the form and try again."
                ),
                "error",
            )

    return render_htmx_template(
        "core/group.html",
        "core/partial/group-members.html",
        form=form,
        menuitem="groups",
        edited_group=group,
        table_form=table_form,
    )


def redirect_after_ownership_change(user, group):
    """Redirect to the group, or to the group list if the user cannot manage it anymore."""
    if group.is_editable_by(user):
        return redirect(url_for("core.groups.group", group=group))

    return redirect(url_for("core.groups.groups"))


def delete_member(user, group, edit_form):
    form = DeleteGroupMemberForm(request.form or None, group=group)
    if form.member.data and not group.member_is_removable_by(user, form.member.data):
        abort(403)

    if not form.validate():
        flash(
            "\n".join(str(e) for e in form.errors.get("member")),
            "error",
        )

    elif form.action.data == "confirm-remove-member":
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
        if form.member.data in group.owners:
            group.owners = [
                owner for owner in group.owners if owner != form.member.data
            ]
        Backend.instance.save(group)

    return edit_group(user, group, edit_form)


def delete_group(group):
    flash(
        _(
            "The group %(group)s has been successfully deleted.",
            group=group.display_name,
        ),
        "success",
    )
    Backend.instance.delete(group)
    return redirect(url_for("core.groups.groups"))


def step_down(user, group, form):
    """Remove the ownership of the user on the group."""
    if user not in group.owners or not group.owner_is_removable_by(user, user):
        abort(403)

    if form.action.data == "confirm-step-down":
        return render_template(
            "core/modals/step-down-group-owner.html", group=group, form=form
        )

    group.owners = [owner for owner in group.owners if owner != user]
    Backend.instance.save(group)
    flash(
        _(
            "You are no longer an owner of the group %(group)s.",
            group=group.display_name,
        ),
        "success",
    )
    return redirect_after_ownership_change(user, group)


@bp.route("/<group:group>/leave", methods=["POST"])
@user_needed()
def leave_group(user, group):
    """Allow a user to leave a group and remove ownership if they are an owner."""
    if user not in group.members:
        flash(_("You are not a member of this group."), "error")
        return redirect(url_for("core.account.index"))

    if user in group.owners and not group.owner_is_removable_by(user, user):
        flash(
            _(
                "You cannot leave %(group)s because you are its last owner.",
                group=group.display_name,
            ),
            "error",
        )
        return redirect(url_for("core.groups.groups"))

    if group.members == [user]:
        flash(
            _(
                "You cannot leave %(group)s because you are its last member.",
                group=group.display_name,
            ),
            "error",
        )
        return redirect(url_for("core.groups.groups"))

    group.members = [member for member in group.members if member != user]

    if user in group.owners:
        group.owners = [owner for owner in group.owners if owner != user]

    Backend.instance.save(group)

    flash(_("You have left %(group)s.", group=group.display_name), "success")
    return redirect(url_for("core.groups.groups"))


@bp.route("/<group:group>/add-members", methods=["GET", "POST"])
@user_needed("manage_all_groups")
def add_members(user, group):
    """Add users to a group, without asking them."""
    form = AddGroupMembersForm(request.form or None, group=group)

    if form.validate_on_submit():
        new_members = [
            member for member in form.new_members.data if member not in group.members
        ]
        group.members = list(group.members) + new_members
        Backend.instance.save(group)
        flash(
            ngettext(
                "%(num)d member has been added to the group %(group)s.",
                "%(num)d members have been added to the group %(group)s.",
                len(new_members),
                group=group.display_name,
            ),
            "success",
        )
        return redirect(url_for("core.groups.group", group=group))

    if request.form and not form.mutated:
        flash(
            _("The members couldn't be added. Please check the form and try again."),
            "error",
        )

    return render_template(
        "core/add_group_members.html", form=form, group=group, menuitem="groups"
    )


@bp.route("/<group:group>/invite", methods=["GET", "POST"])
@smtp_needed()
@user_needed()
def invite_to_group(user, group):
    """Send an invitation email to a user to join a group."""
    if not user_can_access_group(user, group):
        abort(403)

    form = GroupInvitationForm(request.form or None, group=group)
    form_validated = False
    invitation_url = None

    if form.validate_on_submit():
        form_validated = True
        invited_user = Backend.instance.query(models.User, emails=form.email.data)[0]

        expiration_date = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
            seconds=current_app.config["CANAILLE"]["INVITATION_EXPIRATION"]
        )
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id=group.id,
            invited_user_id=invited_user.id,
            invite_as_owner=form.invite_as_owner.data,
        )

        invitation_url = url_for(
            "core.groups.join_group",
            data=payload.b64(),
            hash=payload.build_hash(),
            _external=True,
        )

        send_group_invitation_mail(
            form.email.data,
            invitation_url,
            group.display_name,
            user.formatted_name,
            as_owner=form.invite_as_owner.data,
        )

        flash(
            _("An invitation email has been sent to %(email)s.", email=form.email.data),
            "info",
        )

    return render_template(
        "core/invite_group_member.html",
        form=form,
        group=group,
        menuitem="groups",
        form_validated=form_validated,
        invitation_url=invitation_url,
    )


@bp.route("/join/<data>/<hash>", methods=["GET", "POST"])
def join_group(data, hash):
    """Handle group invitation link validation and add user to group."""
    data_obj = b64_to_obj(data)
    if data_obj is None:
        flash(_("The invitation link that brought you here was invalid."), "error")
        return redirect(url_for("core.account.index"))
    payload = GroupInvitationPayload(*data_obj)

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

    form = Form(request.form or None)
    if request.method == "GET" or not form.validate():
        return render_template(
            "core/modals/join-group.html",
            group=group,
            form=form,
            as_owner=payload.invite_as_owner,
        )

    group.members = list(group.members) + [g.session.user]
    if payload.invite_as_owner:
        group.owners = list(group.owners) + [g.session.user]
    Backend.instance.save(group)

    flash(
        _("You have successfully joined %(group)s!", group=group.display_name),
        "success",
    )
    return redirect(
        url_for("core.account.profile_settings", edited_user=g.session.user)
    )
