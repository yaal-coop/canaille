from canaille.app import models
from canaille.app.flask import permissions_needed
from canaille.app.flask import render_htmx_template
from canaille.app.forms import TableForm
from canaille.app.i18n import gettext as _
from canaille.app.themes import render_template
from flask import abort
from flask import Blueprint
from flask import flash
from flask import redirect
from flask import request
from flask import url_for

from .forms import CreateGroupForm
from .forms import EditGroupForm

bp = Blueprint("groups", __name__, url_prefix="/groups")


@bp.route("/", methods=["GET", "POST"])
@permissions_needed("manage_groups")
def groups(user):
    table_form = TableForm(models.Group, formdata=request.form)
    if request.form and request.form.get("page") and not table_form.validate():
        abort(404)

    return render_htmx_template("groups.html", menuitem="groups", table_form=table_form)


@bp.route("/add", methods=("GET", "POST"))
@permissions_needed("manage_groups")
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
            group.save()
            flash(
                _(
                    "The group %(group)s has been sucessfully created",
                    group=group.display_name,
                ),
                "success",
            )
            return redirect(url_for("core.groups.group", group=group))

    return render_template(
        "group.html", menuitem="groups", form=form, edited_group=None, members=None
    )


@bp.route("/<group:group>", methods=("GET", "POST"))
@permissions_needed("manage_groups")
def group(user, group):
    if (
        request.method == "GET"
        or request.form.get("action") == "edit"
        or request.form.get("page")
    ):
        return edit_group(group)

    if request.form.get("action") == "confirm-delete":
        return render_template("modals/delete-group.html", group=group)

    if request.form.get("action") == "delete":
        return delete_group(group)

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

    if request.form and not request.form.get("page"):
        if form.validate():
            group.description = form.description.data
            group.save()
            flash(
                _(
                    "The group %(group)s has been sucessfully edited.",
                    group=group.display_name,
                ),
                "success",
            )
            return redirect(url_for("core.groups.group", group=group))
        else:
            flash(_("Group edition failed."), "error")

    return render_htmx_template(
        "group.html",
        "partial/users.html",
        form=form,
        menuitem="groups",
        edited_group=group,
        table_form=table_form,
    )


def delete_group(group):
    flash(
        _("The group %(group)s has been sucessfully deleted", group=group.display_name),
        "success",
    )
    group.delete()
    return redirect(url_for("core.groups.groups"))
