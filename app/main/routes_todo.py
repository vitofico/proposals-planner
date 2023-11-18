from flask import render_template, redirect, url_for, flash, jsonify
from flask_login import login_required


from app import db
from app.main import bp
from app.main.forms import ToDoForm
from app.models import Proposal, ACCESS, User, ToDo
from app.custom_libs.utilities_lib import requires_access_level, role_required


# ToDos

@bp.route("/<proposal_acronym>/todos", methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def proposal_todos(proposal_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    todos = proposal.todos
    todo = ToDo()
    form = ToDoForm(proposal=proposal, obj=todo)

    if form.validate_on_submit():
        form.populate_obj(todo)
        user = User.query.filter_by(username=form.data['assigned_to']).first()
        flash_message = 'Todo Added!'
        try:
            proposal.todos.append(todo)
            user.todos.append(todo)
            db.session.commit()
        except Exception as inst:
            flash_message = f'error! {inst}'
        flash(flash_message)
        return jsonify(status='ok')
    return render_template('todos.html', title='ToDos', form=form, todos=todos, proposal=proposal)

@bp.route("/<proposal_acronym>/todos/edit/<todo_id>", methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def proposal_todos_edit(proposal_acronym, todo_id):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    todo = ToDo.query.get(todo_id)
    form = ToDoForm(proposal=proposal, obj=todo)
    if form.validate_on_submit():
        form.populate_obj(todo)
        user = User.query.filter_by(username=form.data['assigned_to']).first()
        flash_message = 'Todo Added!'
        try:
            todo.assigned_to = user.id
            db.session.commit()
        except Exception as inst:
            flash_message = f'error! {inst}'
        flash(flash_message)
        return redirect(url_for('main.proposal_todos', proposal_acronym=proposal.acronym))
    return render_template('quick_form.html', title='ToDos', form=form)

@bp.route("/<proposal_acronym>/todos/remove/<todo_id>", methods=['GET', 'POST'])
@role_required('responsible')
@requires_access_level(ACCESS['user'])
@login_required
def proposal_todos_remove(proposal_acronym, todo_id):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    todo = ToDo.query.get(todo_id)
    proposal.todos.remove(todo)
    flash_message = 'The To-Do has been removed!'
    try:
        db.session.commit()
    except Exception as inst:
        flash_message = f'error! {inst}'
    flash(flash_message)
    return redirect(url_for('main.proposal_todos', proposal_acronym=proposal.acronym))
