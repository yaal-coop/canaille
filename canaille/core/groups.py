from canaille.app.flask import permissions_needed
from canaille.app.flask import render_htmx_template
from canaille.app.forms import TableForm
from flask import abort
from flask import Blueprint
from flask import flash
from flask import redirect
from flask import request
from flask import url_for
from flask_babel import gettext as _
from flask_themer import render_template

from .forms import CreateGroupForm
from .forms import EditGroupForm
from .models import Group
from .models import User

bp = Blueprint("groups", __name__, url_prefix="/groups")


@bp.route("/", methods=["GET", "POST"])
@permissions_needed("manage_groups")
def groups(user):
    table_form = TableForm(Group, formdata=request.form)
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
            group = Group()
            group.members = [user]
            group.display_name = [form.display_name.data]
            group.description = [form.description.data]
            group.save()
            flash(
                _(
                    "The group %(group)s has been sucessfully created",
                    group=group.display_name,
                ),
                "success",
            )
            return redirect(url_for("groups.group", groupname=group.display_name))

    return render_template(
        "group.html", menuitem="groups", form=form, edited_group=None, members=None
    )


@bp.route("/<groupname>", methods=("GET", "POST"))
@permissions_needed("manage_groups")
def group(user, groupname):
    group = Group.get(groupname)

    if not group:
        abort(404)

    if (
        request.method == "GET"
        or request.form.get("action") == "edit"
        or request.form.get("page")
    ):
        return edit_group(group)

    if request.form.get("action") == "delete":
        return delete_group(group)

    abort(400)


def edit_group(group):
    table_form = TableForm(User, filter={"groups": group}, formdata=request.form)
    if request.form and request.form.get("page") and not table_form.validate():
        abort(404)

    form = EditGroupForm(
        request.form or None,
        data={
            "display_name": group.display_name,
            "description": group.description[0] if group.description else "",
        },
    )

    if request.form and not request.form.get("page"):
        if form.validate():
            group.description = [form.description.data]
            group.save()
            flash(
                _(
                    "The group %(group)s has been sucessfully edited.",
                    group=group.display_name,
                ),
                "success",
            )
            return redirect(url_for("groups.group", groupname=group.display_name))
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
    return redirect(url_for("groups.groups"))
