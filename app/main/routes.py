import json
import os
import shutil
from datetime import datetime

import pypandoc
from flask import render_template, redirect, request, url_for, g, flash, send_from_directory, Response
from flask_babel import _, get_locale
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app import db
from app.custom_libs.highcharts_lib import to_highchart, to_gantt_highchart, to_map_highchart
from app.custom_libs.print_lib import ProposalText
from app.custom_libs.tables_lib import get_WP_table, get_budget_table, get_WPeffort_table, \
    get_proposal_deliverable_table, \
    get_proposal_milestone_table
from app.custom_libs.trello_lib import send_proposal_to_trello
from app.custom_libs.utilities_lib import add_admin_user, add_proposal_statuses, requires_access_level, role_required, \
    color_diff, create_folder, make_tree
from app.main import bp
from app.main.forms import ProposalForm, ParticipantForm, UserPermissionForm, \
    UploadForm
from app.models import Proposal, Company, ProposalStatus, date_format, ACCESS, User, ROLES


@bp.app_template_filter()
def show_diff_table(change):
    diff = color_diff(change)
    return '<p>' + ''.join(diff) + '</p>'


@bp.before_app_request
def before_request():
    g.user = current_user
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
    g.locale = str(get_locale())
    add_admin_user()
    add_proposal_statuses()


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    proposals = Proposal.query.all()
    return render_template('index.html', title=_('Home'), proposals=proposals)


# Proposal

@bp.route('/add_proposal', methods=['GET', 'POST'])
@login_required
@requires_access_level(ACCESS['admin'])
def add_proposal():
    form = ProposalForm(request.form)
    if form.validate_on_submit():
        data = request.form.to_dict()
        date_obj = datetime.strptime(data['start_date'], date_format)
        proposal = Proposal(acronym=data['acronym'], title=data['title'], description=data['description'],
                            budget=data['budget'], indirect_costs_rate=int(data['indirect_costs_rate_percent']) / 100,
                            call=data['call'], start_date=date_obj, duration_months=data['duration_months'],
                            topic=data['topic'],
                            status=ProposalStatus.get_status(data['status']), action_type=data['action_type'])
        flash_message = 'Your proposal has been added!'
        try:
            db.session.add(proposal)
            db.session.commit()
        except Exception as inst:
            flash_message = f'error! {inst}'
        flash(flash_message)
        proposal.add_user(current_user, role=ROLES['responsible'])
        return redirect(url_for('main.index'))
    return render_template('quick_form.html', title='Add Proposal', form=form)


@bp.route('/<proposal_acronym>/dashboard', methods=['GET'])
@role_required('read_only')
@requires_access_level(ACCESS['user'])
@login_required
def dashboard(proposal_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    series, series_drilldown = proposal.serialise_budget()
    chart = to_highchart(graphtype='pie', series=series, series_drilldown=series_drilldown, title='Budget Shares',
                         subtitle='Click the slices to view the budget detail')
    wp_table = get_WP_table(proposal_acronym)
    effort_table = get_WPeffort_table(proposal_acronym)
    budget_table = get_budget_table(proposal_acronym)
    deliverables_table = get_proposal_deliverable_table(proposal_acronym)
    milestones_table = get_proposal_milestone_table(proposal_acronym)
    gantt = to_gantt_highchart(proposal.get_gantt_data(), 'Gantt Chart')
    map = to_map_highchart(proposal.get_map_data(), 'Participants Geographical Distribution')
    tree = make_tree(create_folder(proposal_acronym))
    return render_template('dashboard.html', proposal=proposal, chart=chart, gantt=gantt, wp_table=wp_table,
                           budget_table=budget_table, effort_table=effort_table, deliverables_table=deliverables_table,
                           milestones_table=milestones_table, map=map, tree=tree)


@bp.route('/<proposal_acronym>/edit', methods=['GET', 'POST'])
@role_required('responsible')
@requires_access_level(ACCESS['user'])
@login_required
def edit_proposal(proposal_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    form = ProposalForm(request.form, obj=proposal)
    if form.validate_on_submit():
        data = request.form.to_dict()
        proposal.update(data)
        flash_message = 'Your proposal has been modified successfully!'
        try:
            db.session.commit()
        except Exception as inst:
            flash_message = f'error! {inst}'
        flash(flash_message)
        return redirect(url_for('main.dashboard', proposal_acronym=proposal.acronym))
    return render_template('quick_form.html', title='Edit Proposal', form=form)


@bp.route('/<proposal_acronym>/delete', methods=['GET', 'POST'])
@role_required('responsible')
@requires_access_level(ACCESS['admin'])
@login_required
def delete_proposal(proposal_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    folder = create_folder(proposal_acronym)
    shutil.rmtree(folder, ignore_errors=True)
    proposal.delete()
    flash_message = 'Your proposal has been deleted!'
    try:
        db.session.commit()
    except Exception as inst:
        flash_message = f'error! {inst}'
    flash(flash_message)


# Exporting

@bp.route('/<proposal_acronym>/export', methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def export_proposal(proposal_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    if request.args:
        format = request.args['format']
    else:
        format = ''
    text = ProposalText(proposal)
    filename = text.write_description()
    new_filename = os.path.splitext(filename)[0] + f'.{format}'
    pypandoc.convert_file(filename, format, outputfile=new_filename)
    os.remove(filename)
    return send_from_directory(directory=os.path.dirname(new_filename), filename=os.path.basename(new_filename),
                               as_attachment=True)


# Participants


@bp.route('/<proposal_acronym>/add_participant', methods=['GET', 'POST'])
@role_required('responsible')
@requires_access_level(ACCESS['user'])
@login_required
def add_participant(proposal_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    form = ParticipantForm.new(obj=None)
    d_temp = {'y': True, 'n': False}
    if form.validate_on_submit():
        data = request.form.to_dict()
        if 'is_coordinator' not in data:
            data['is_coordinator'] = 'n'
        proposal.add_participant(Company.get_company_acronym(data['participant']),
                                 personnel_cost=data['personnel_cost'],
                                 subcontracting_cost=data['subcontracting_cost'],
                                 is_coordinator=d_temp[data['is_coordinator']],
                                 participant_number=data['participant_number'],
                                 other_direct_costs=data['other_direct_costs'],
                                 proposal_related_text=data['proposal_related_text'])
        flash_message = 'The proposal has been correctly modified!'
        flash(flash_message)
        return redirect(url_for('main.dashboard', proposal_acronym=proposal.acronym))
    return render_template('quick_form.html', title='Add Participant', form=form)


@bp.route('/<proposal_acronym>/edit_participant/<company_acronym>', methods=['GET', 'POST'])
@role_required('responsible')
@requires_access_level(ACCESS['user'])
@login_required
def edit_participant(proposal_acronym, company_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    participant = proposal.get_participant(Company.get_company_acronym(company_acronym))
    form = ParticipantForm.new(obj=participant, company=participant.company)
    d_temp = {'y': True, 'n': False}
    if form.validate_on_submit():
        data = request.form.to_dict()
        if 'is_coordinator' not in data:
            data['is_coordinator'] = 'n'
        proposal.add_participant(Company.get_company_acronym(data['participant']),
                                 personnel_cost=data['personnel_cost'],
                                 subcontracting_cost=data['subcontracting_cost'],
                                 is_coordinator=d_temp[data['is_coordinator']],
                                 participant_number=data['participant_number'],
                                 other_direct_costs=data['other_direct_costs'],
                                 proposal_related_text=data['proposal_related_text'])
        flash_message = 'The proposal has been correctly modified!'
        flash(flash_message)
        return redirect(url_for('main.dashboard', proposal_acronym=proposal.acronym))
    return render_template('quick_form.html', title='Add Participant', form=form)


@bp.route('/<proposal_acronym>/remove_participant/<company_acronym>', methods=['GET', 'POST'])
@role_required('responsible')
@requires_access_level(ACCESS['user'])
@login_required
def remove_participant(proposal_acronym, company_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    proposal.remove_participant(Company.get_company_acronym(company_acronym))
    return redirect(url_for('main.dashboard', proposal_acronym=proposal.acronym))


# Users

@bp.route('/<proposal_acronym>/add_user', methods=['GET', 'POST'])
@role_required('responsible')
@requires_access_level(ACCESS['user'])
@login_required
def add_user(proposal_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    form = UserPermissionForm.new()
    if form.validate_on_submit():
        data = request.form.to_dict()
        proposal.add_user(User.query.filter_by(username=data['user']).first(), role=int(data['role']))
        flash_message = 'The user has been correctly added to the proposal!'
        flash(flash_message)
        return redirect(url_for('main.dashboard', proposal_acronym=proposal.acronym))
    return render_template('quick_form.html', title='Add User', form=form)


@bp.route('/<proposal_acronym>/remove_user/<username>', methods=['GET', 'POST'])
@role_required('responsible')
@requires_access_level(ACCESS['user'])
@login_required
def remove_user(proposal_acronym, username):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    proposal.remove_user(User.query.filter_by(username=username).first())
    return redirect(url_for('main.dashboard', proposal_acronym=proposal.acronym))


# Files

@bp.route("/<proposal_acronym>/downloads/<path:filename>", methods=['GET', 'POST'])
@role_required('read_only')
@requires_access_level(ACCESS['user'])
@login_required
def get_file(proposal_acronym, filename):
    """Download a file."""
    folder = create_folder(proposal_acronym)
    return send_from_directory(directory=folder, filename=filename, as_attachment=True)


@bp.route("/<proposal_acronym>/delete/<path:filename>", methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def delete_file(proposal_acronym, filename):
    """delete a file."""
    folder = create_folder(proposal_acronym)
    if os.path.exists(os.path.join(folder, filename)):
        os.remove(os.path.join(folder, filename))
        flashmessage = f'the file "{filename}" has been deleted'
    else:
        flashmessage = f'the file "{filename}" does not exist'
    flash(flashmessage)
    return redirect(url_for('main.dashboard', proposal_acronym=proposal_acronym))


@bp.route("/<proposal_acronym>/upload", methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def upload_file(proposal_acronym):
    folder = create_folder(proposal_acronym)
    form = UploadForm()
    if form.validate_on_submit():
        if request.method == 'POST':
            # check if the post request has the file part
            f = form.submitted_file.data
            filename = secure_filename(f.filename)
            uploaded_file = os.path.join(folder, filename)
            f.save(uploaded_file)
            flash_message = 'File correctly submitted'
            flash(flash_message)
            return redirect(url_for('main.dashboard', proposal_acronym=proposal_acronym))
    return render_template('quick_form.html', title='Submit File', form=form)


# Changelog

@bp.route('/<proposal_acronym>/restore_version/<version_index>', methods=['GET', 'POST'])
@role_required('responsible')
@requires_access_level(ACCESS['user'])
@login_required
def restore_proposal_version(proposal_acronym, version_index):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    version = proposal.versions[int(version_index)]
    version.revert()
    db.session.commit()
    flash_message = f'Proposal Restored to version {version_index}'
    flash(flash_message)
    return redirect(url_for('main.dashboard', proposal_acronym=proposal.acronym))


@bp.route("/<proposal_acronym>/changelog", methods=['GET', 'POST'])
@role_required('read_only')
@requires_access_level(ACCESS['user'])
@login_required
def proposal_changelog(proposal_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    return render_template('changelog.html', proposal=proposal)


### Trello
@bp.route("/<proposal_acronym>/totrello", methods=['GET', 'POST'])
@role_required('responsible')
@requires_access_level(ACCESS['user'])
@login_required
def submit_to_trello(proposal_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    ## Execute in thread - currently not working for db problem
    # user = User.query.filter_by(username=current_user.username).first()
    # Thread(target=execute_send_trello,
    #        args=(current_app._get_current_object(), proposal, user)).start()
    if current_user.trello_token and current_user.trello_api_key:
        message=send_proposal_to_trello(proposal=proposal, user=current_user)
        flash(message)
        return redirect(url_for('main.dashboard', proposal_acronym=proposal.acronym))
    else:
        flash('Please set your Trello user api key and token')
        return redirect(url_for('main.user_panel', username=current_user.username))



### Autocomplete

@bp.route('/_autocomplete/<item>', methods=['GET'])
def autocomplete(item):
    if item == 'topic':
        return Response(json.dumps(Proposal.get_topics_list()), mimetype='application/json')
    elif item == 'call':
        return Response(json.dumps(Proposal.get_calls_list()), mimetype='application/json')
