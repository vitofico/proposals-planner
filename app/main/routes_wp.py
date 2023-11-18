from flask import render_template, redirect, request, url_for, flash
from flask_login import login_required

from app import db
from app.custom_libs.highcharts_lib import to_highchart
from app.main import bp
from app.main.forms import WPForm, WPParticipantForm, DeliverableForm, MilestoneForm
from app.models import Proposal, Company, WP, ACCESS, Deliverable, Milestone
from app.custom_libs.tables_lib import get_wp_deliverable_table, get_wp_milestone_table
from app.custom_libs.utilities_lib import requires_access_level, role_required


@bp.route('/<proposal_acronym>/add_wp', methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def add_wp(proposal_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    wp = WP()
    form = WPForm.new(obj=wp, proposal=proposal)
    if form.validate_on_submit():
        form.populate_obj(wp)
        proposal.working_packages.append(wp)
        flash_message = 'The Work Package has been added!'
        try:
            db.session.commit()
        except Exception as inst:
            flash_message = f'error! {inst}'
        flash(flash_message)
        return redirect(url_for('main.dashboard', proposal_acronym=proposal.acronym))
    return render_template('quick_form.html', title='Add Work Package', form=form)


@bp.route('/<proposal_acronym>/remove_wp/WP<wp_number>', methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def remove_wp(proposal_acronym, wp_number):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    wp = WP.get_wp(proposal, wp_number)
    proposal.working_packages.remove(wp)
    flash_message = 'The Work Package has been removed!'
    try:
        db.session.commit()
    except Exception as inst:
        flash_message = f'error! {inst}'
    flash(flash_message)
    return redirect(url_for('main.dashboard', proposal_acronym=proposal.acronym))


@bp.route('/<proposal_acronym>/WP<wp_number>', methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def wp_dashboard(proposal_acronym, wp_number):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    wp = WP.get_wp(proposal, wp_number)
    if wp and proposal:
        chart = to_highchart(graphtype='pie', series=wp.serialise_pm(), series_drilldown='', title='PM Distribution',
                             value_label='PM', subtitle='')
        deliverable_table = get_wp_deliverable_table(wp)
        milestone_table = get_wp_milestone_table(wp)
        return render_template('wp_dashboard.html', title='WP Dashboard', wp=wp, proposal=proposal, chart=chart,
                               deliverable_table=deliverable_table, milestone_table=milestone_table)
    else:
        return render_template('errors/404.html')


@bp.route('/<proposal_acronym>/WP<wp_number>/edit', methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def edit_wp(proposal_acronym, wp_number):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    wp = WP.get_wp(proposal, wp_number)
    form = WPForm.new(obj=wp, proposal=proposal)
    if form.validate_on_submit():
        form.populate_obj(wp)
        flash_message = 'The Work Package has been edited!'
        try:
            db.session.commit()
        except Exception as inst:
            flash_message = f'error! {inst}'
        flash(flash_message)
        return redirect(url_for('main.wp_dashboard', proposal_acronym=proposal.acronym, wp_number=wp.number))
    return render_template('quick_form.html', title='Edit Work Package', form=form)


# Participant

@bp.route('/<proposal_acronym>/WP<wp_number>/add_participant', methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def add_WP_participant(proposal_acronym, wp_number):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    wp = WP.get_wp(proposal, wp_number)
    form = WPParticipantForm.new(obj=None, proposal=proposal)
    d_temp = {'y': True, 'n': False}
    if form.validate_on_submit():
        data = request.form.to_dict()
        if 'leader' not in data:
            data['leader'] = 'n'
        wp.add_participant(Company.get_company_acronym(data['participant']),
                           person_month=data['person_month'], leader=d_temp[data['leader']])
        flash_message = 'The participant has been added!'
        flash(flash_message)
        return redirect(url_for('main.wp_dashboard', proposal_acronym=proposal.acronym, wp_number=wp.number))
    return render_template('quick_form.html', title='Add WP Participant', form=form)


@bp.route('/<proposal_acronym>/WP<wp_number>/remove_participant/<company_acronym>', methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def remove_WP_participant(proposal_acronym, wp_number, company_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    wp = WP.get_wp(proposal, wp_number)
    wp.remove_participant(Company.get_company_acronym(company_acronym))
    return redirect(url_for('main.wp_dashboard', proposal_acronym=proposal.acronym, wp_number=wp.number))


@bp.route('/<proposal_acronym>/WP<wp_number>/edit_participant/<company_acronym>', methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def edit_WP_participant(proposal_acronym, wp_number, company_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    wp = WP.get_wp(proposal, wp_number)
    participant = wp.get_participant(Company.get_company_acronym(company_acronym))
    form = WPParticipantForm.new(obj=participant, proposal=proposal,
                                 company=Company.get_company_acronym(company_acronym))
    d_temp = {'y': True, 'n': False}
    if form.validate_on_submit():
        data = request.form.to_dict()
        if 'leader' not in data:
            data['leader'] = 'n'
        wp.add_participant(Company.get_company_acronym(data['participant']),
                           person_month=data['person_month'], leader=d_temp[data['leader']])
        flash_message = 'The participant has been modified!'
        flash(flash_message)
        return redirect(url_for('main.wp_dashboard', proposal_acronym=proposal.acronym, wp_number=wp.number))
    return render_template('quick_form.html', title='Edit WP Participant', form=form)


# Deliverables

@bp.route('/<proposal_acronym>/WP<wp_number>/add_deliverable', methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def add_WP_deliverable(proposal_acronym, wp_number):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    wp = WP.get_wp(proposal, wp_number)
    deliverable = Deliverable()
    form = DeliverableForm.new(obj=deliverable, wp=wp)
    if form.validate_on_submit():
        form.populate_obj(deliverable)
        wp.deliverables.append(deliverable)
        flash_message = 'The deliverable has been added!'
        try:
            db.session.commit()
        except Exception as inst:
            flash_message = f'error! {inst}'
        flash(flash_message)
        return redirect(url_for('main.wp_dashboard', proposal_acronym=proposal.acronym, wp_number=wp.number))
    return render_template('quick_form.html', title='Add Deliverable', form=form)


@bp.route('/<proposal_acronym>/WP<wp_number>/remove_deliverable/<deliverable_number>', methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def remove_WP_deliverable(proposal_acronym, wp_number, deliverable_number):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    wp = WP.get_wp(proposal, wp_number)
    deliverable = Deliverable.get_bynumber(wp=wp, number=deliverable_number)
    wp.deliverables.remove(deliverable)
    flash_message = 'The Deliverable has been removed!'
    try:
        db.session.commit()
    except Exception as inst:
        flash_message = f'error! {inst}'
    flash(flash_message)
    return redirect(url_for('main.wp_dashboard', proposal_acronym=proposal.acronym, wp_number=wp.number))


@bp.route('/<proposal_acronym>/WP<wp_number>/edit_deliverable/<deliverable_number>', methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def edit_WP_deliverable(proposal_acronym, wp_number, deliverable_number):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    wp = WP.get_wp(proposal, wp_number)
    deliverable = Deliverable.get_bynumber(wp=wp, number=deliverable_number)
    form = DeliverableForm.new(obj=deliverable, wp=wp)
    if form.validate_on_submit():
        form.populate_obj(deliverable)
        wp.deliverables.append(deliverable)
        flash_message = 'The deliverable has been added!'
        try:
            db.session.commit()
        except Exception as inst:
            flash_message = f'error! {inst}'
        flash(flash_message)
        return redirect(url_for('main.wp_dashboard', proposal_acronym=proposal.acronym, wp_number=wp.number))
    return render_template('quick_form.html', title='Edit Deliverable', form=form)


### Milestones

@bp.route('/<proposal_acronym>/WP<wp_number>/add_milestone', methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def add_WP_milestone(proposal_acronym, wp_number):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    wp = WP.get_wp(proposal, wp_number)
    milestone = Milestone()
    form = MilestoneForm.new(obj=milestone, wp=wp)
    if form.validate_on_submit():
        form.populate_obj(milestone)
        wp.milestones.append(milestone)
        flash_message = 'The milestone has been added!'
        try:
            db.session.commit()
        except Exception as inst:
            flash_message = f'error! {inst}'
        flash(flash_message)
        return redirect(url_for('main.wp_dashboard', proposal_acronym=proposal.acronym, wp_number=wp.number))
    return render_template('quick_form.html', title='Add Milestone', form=form)


@bp.route('/<proposal_acronym>/WP<wp_number>/remove_milestone/<milestone_number>', methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def remove_WP_milestone(proposal_acronym, wp_number, milestone_number):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    wp = WP.get_wp(proposal, wp_number)
    milestone = Milestone.get_bynumber(wp=wp, number=milestone_number)
    wp.milestones.remove(milestone)
    flash_message = 'The Milestone has been removed!'
    try:
        db.session.commit()
    except Exception as inst:
        flash_message = f'error! {inst}'
    flash(flash_message)
    return redirect(url_for('main.wp_dashboard', proposal_acronym=proposal.acronym, wp_number=wp.number))


@bp.route('/<proposal_acronym>/WP<wp_number>/edit_milestone/<milestone_number>', methods=['GET', 'POST'])
@role_required('edit')
@requires_access_level(ACCESS['user'])
@login_required
def edit_WP_milestone(proposal_acronym, wp_number, milestone_number):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    wp = WP.get_wp(proposal, wp_number)
    milestone = Milestone.get_bynumber(wp=wp, number=milestone_number)
    form = MilestoneForm.new(obj=milestone, wp=wp)
    if form.validate_on_submit():
        form.populate_obj(milestone)
        wp.milestones.append(milestone)
        flash_message = 'The Milestone has been modified!'
        try:
            db.session.commit()
        except Exception as inst:
            flash_message = f'error! {inst}'
        flash(flash_message)
        return redirect(url_for('main.wp_dashboard', proposal_acronym=proposal.acronym, wp_number=wp.number))
    return render_template('quick_form.html', title='Edit Milestone', form=form)


### Changelog

@bp.route('/restore_wp/WP<wp_id>/<version_index>', methods=['GET', 'POST'])
@role_required('responsible')
@requires_access_level(ACCESS['user'])
@login_required
def restore_wp_version(wp_id, version_index):
    wp = WP.query.get(int(wp_id))
    proposal = wp.ref_proposal
    version = wp.versions[int(version_index)]
    version.revert()
    db.session.commit()
    flash_message = f'WP Restored to version {version_index}'
    flash(flash_message)
    return redirect(url_for('main.wp_dashboard', proposal_acronym=proposal.acronym, wp_number=wp.number))
