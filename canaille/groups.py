from flask import abort
from flask import Blueprint
from flask import current_app
from flask import flash
from flask import redirect
from flask import request
from flask import url_for
from flask_babel import gettext as _
from flask_themer import render_template

from .flaskutils import permissions_needed
from .forms import GroupForm
from .forms import unique_group
from .models import Group

bp = Blueprint("groups", __name__, url_prefix="/groups")


@bp.route("/")
@permissions_needed("manage_groups")
def groups(user):
    groups = Group.all()
    return render_template("groups.html", groups=groups, menuitem="groups")


@bp.route("/add", methods=("GET", "POST"))
@permissions_needed("manage_groups")
def create_group(user):
    form = GroupForm(request.form or None)

    try:
        if "name" in form:
            del form["name"].render_kw["readonly"]
            form["name"].validators.append(unique_group)
    except KeyError:
        pass

    if request.form:
        if not form.validate():
            flash(_("Group creation failed."), "error")
        else:
            group = Group(
                objectClass=current_app.config["LDAP"].get(
                    "GROUP_CLASS", Group.DEFAULT_OBJECT_CLASS
                )
            )
            group.member = [user.dn]
            group.cn = [form.name.data]
            group.description = [form.description.data]
            group.save()
            flash(
                _("The group %(group)s has been sucessfully created", group=group.name),
                "success",
            )
            return redirect(url_for("groups.group", groupname=group.name))

    return render_template("group.html", form=form, edited_group=None, members=None)


@bp.route("/<groupname>", methods=("GET", "POST"))
@permissions_needed("manage_groups")
def group(user, groupname):
    group = Group.get(groupname)

    if not group:
        abort(404)

    if request.method == "GET" or request.form.get("action") == "edit":
        return edit_group(group)

    if request.form.get("action") == "delete":
        return delete_group(group)

    abort(400)


def edit_group(group):
    form = GroupForm(
        request.form or None,
        data={
            "name": group.name,
            "description": group.description[0] if group.description else "",
        },
    )
    form["name"].render_kw["readonly"] = "true"

    if request.form:
        if form.validate():
            group.description = [form.description.data]
            group.save()
            return redirect(url_for("groups.group", groupname=group.name))
        else:
            flash(_("Group edition failed."), "error")

    return render_template(
        "group.html", form=form, edited_group=group, members=group.get_members()
    )


def delete_group(group):
    flash(
        _("The group %(group)s has been sucessfully deleted", group=group.name),
        "success",
    )
    group.delete()
    return redirect(url_for("groups.groups"))
