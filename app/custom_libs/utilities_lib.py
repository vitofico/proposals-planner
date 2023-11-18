from datetime import datetime
import difflib
import functools
import os

from flask import url_for, redirect, current_app, abort, request, flash
from flask_admin.contrib import sqla
from flask_login import current_user

from app import db
from app.models import User, ACCESS, ProposalStatus, ROLES


def try_except_decorator(func):
    @functools.wraps(func)
    def wrapper_decorator(*args, **kwargs):
        try:
            value = func(*args, **kwargs)
        except Exception as e:
            flash(e)
            value = None
        # Do something after
        return value

    return wrapper_decorator


# @scheduler.task ('cron', id='do_job_2', minute='10', hour='2')
# def clean_logtable():
#     Changelog.delete_expired ()

#### Redirection helper
# Without any parameters it will redirect the user back to where he came from (request.referrer).
# You can add the get parameter next to specify a url

def redirect_url(default='index'):
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)


# --------------- ADMIN functions ------------------------#

def role_required(required_role):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if 'proposal_acronym' in kwargs:
                assigned_role = current_user.proposal_role(kwargs['proposal_acronym'])
                if current_user.is_superuser():
                    return f(*args, **kwargs)
                elif assigned_role is not None:
                    if assigned_role >= ROLES[required_role]:
                        return f(*args, **kwargs)
                    else:
                        flash("You do not have access to that page. Sorry!")
                        return redirect(url_for('main.index'))
                else:
                    flash("You do not have access to that page. Sorry!")
                    return redirect(url_for('main.index'))
            else:
                return f(*args, **kwargs)

        return decorated_function

    return decorator


def requires_access_level(access_level):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.allowed(access_level):
                flash("You do not have access to that page. Sorry!")
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


@try_except_decorator
def add_admin_user():
    user = User.query.filter_by(username='admin').first()
    if not user:
        user = User(username='admin', access=ACCESS['superuser'], name='Admin', surname='Nous')
        user.set_password(current_app.config['ADMIN_PASS'])
        db.session.add(user)
        db.session.commit()


STATUS = ['Draft', 'Completed', 'Sent', 'Accepted', 'Rejected']


@try_except_decorator
def add_proposal_statuses():
    for st in STATUS:
        status = ProposalStatus.query.filter_by(status=st).first()
        if not status:
            status = ProposalStatus(status=st, badge_type="info")
            db.session.add(status)
            db.session.commit()


# --------------- ModelView functions ------------------------#

# Create customized model view class
class MyModelView(sqla.ModelView):
    column_display_pk = True
    column_hide_backrefs = False
    can_view_details = True
    create_modal = True
    edit_modal = True

    def is_accessible(self):
        return (current_user.is_active and
                current_user.is_authenticated and
                current_user.is_superuser()
                )

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('auth.login', next=request.url))


# class ComponentsView(MyModelView):
#     column_searchable_list = ['part_number']

# Template Filters

def color_diff(change):
    diff = difflib.ndiff(str(change[0]).splitlines(), str(change[1]).splitlines())
    for line in diff:
        if line.startswith('+'):
            yield '<span class="text-success">' + line + '</span><br>'
        elif line.startswith('-'):
            yield '<span class="text-danger">' + line + '</span><br>'
        elif line.startswith('?'):
            yield ''
        else:
            yield line


# Files Utilities

def create_folder(name):
    main_route = os.path.join(current_app.root_path, current_app.config['DOWNLOAD_FOLDER'])
    folder_route = os.path.join(main_route, name)
    if not os.path.exists(folder_route):
        os.makedirs(folder_route)
    return folder_route


def make_tree(path):
    tree = dict(name=path, children=[])
    # try: lst = os.listdir(path)
    # except OSError:
    #     pass #ignore errors
    # else:
    #     for name in lst:
    #         fn = os.path.join(path, name)
    #         if os.path.isdir(fn):
    #             tree['children'].append(make_tree(fn))
    #         else:
    #             tree['children'].append(dict(name=fn))
    tree['children'] = [{'filename': f,
                         'date': datetime.fromtimestamp(os.path.getmtime(os.path.join(path, f))).strftime(
                             "%Y%m%d %H:%M")} for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    return tree

# other utils
