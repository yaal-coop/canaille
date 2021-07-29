from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    current_app,
    abort,
)
from flask_babel import gettext as _

from .flaskutils import moderator_needed
from .forms import GroupForm
from .models import Group

bp = Blueprint("groups", __name__)


@bp.route("/")
@moderator_needed()
def groups(user):
    groups = Group.filter(objectClass=current_app.config["LDAP"]["GROUP_CLASS"])
    return render_template("groups.html", groups=groups, menuitem="groups")


@bp.route("/add", methods=("GET", "POST"))
@moderator_needed()
def create_group(user):
    form = GroupForm(request.form or None)
    try:
        if "name" in form:
            del form["name"].render_kw["disabled"]
    except KeyError:
        pass

    if request.form:
        if not form.validate():
            flash(_("Group creation failed."), "error")
        else:
            group = Group(objectClass=current_app.config["LDAP"]["GROUP_CLASS"])
            group.member = [user.dn]
            group.cn = [form.name.data]
            group.save()
            flash(
                _("The group %(group)s has been sucessfully created", group=group.name),
                "success",
            )
            return redirect(url_for("groups.group", groupname=group.name))

    return render_template("group.html", form=form, edited_group=None, members=None)


@bp.route("/<groupname>", methods=("GET", "POST"))
@moderator_needed()
def group(user, groupname):
    group = Group.get(groupname) or abort(404)

    if request.method == "GET" or request.form.get("action") == "edit":
        return edit_group(group)

    if request.form.get("action") == "delete":
        return delete_group(group)

    abort(400)


def edit_group(group):
    form = GroupForm(request.form or None, data={"name": group.name})
    form["name"].render_kw["disabled"] = "true"

    if request.form:
        if form.validate():
            group.save()
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
