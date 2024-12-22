from flask import Blueprint
from flask import abort
from flask import flash
from flask import redirect
from flask import request
from flask import url_for

from canaille.app import models
from canaille.app.flask import render_htmx_template
from canaille.app.flask import user_needed
from canaille.app.forms import TableForm
from canaille.app.i18n import gettext as _
from canaille.app.templating import render_template
from canaille.backends import Backend

from .forms import CreateGroupForm
from .forms import DeleteGroupMemberForm
from .forms import EditGroupForm

bp = Blueprint("groups", __name__, url_prefix="/groups")


@bp.route("/", methods=["GET", "POST"])
@user_needed("manage_groups")
def groups(user):
    table_form = TableForm(models.Group, formdata=request.form)
    if request.form and request.form.get("page") and not table_form.validate():
        abort(404)

    return render_htmx_template(
        "core/groups.html", menuitem="groups", table_form=table_form
    )


@bp.route("/add", methods=("GET", "POST"))
@user_needed("manage_groups")
def create_group(user):
    form = CreateGroupForm(request.form or None)

    if request.form:
        if not form.validate():
            flash(_("Group creation failed."), "error")
        else:
            group = models.Group()
            group.members = [user]
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


@bp.route("/<group:group>", methods=("GET", "POST"))
@user_needed("manage_groups")
def group(user, group):
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
