from flask import render_template, redirect, request, url_for, flash
from flask_login import login_required

from app import db
from app.main import bp
from app.main.forms import CompanyForm
from app.models import Company, ACCESS
from app.custom_libs.utilities_lib import requires_access_level


@bp.route('/companies', methods=['GET', 'POST'])
@requires_access_level(ACCESS['admin'])
@login_required
def companies():
    comps = Company.query.all()
    if request.args:
        searchtext = request.args['searchtext']
    else:
        searchtext = ''
    return render_template('companies.html', companies=comps, searchtext=searchtext)


@bp.route('/add_company', methods=['GET', 'POST'])
@requires_access_level(ACCESS['admin'])
@login_required
def add_company():
    company = Company()
    form = CompanyForm(request.form, obj=company)
    if form.validate_on_submit():
        form.populate_obj(company)
        flash_message = 'The company has been added!'
        try:
            db.session.add(company)
            db.session.commit()
        except Exception as inst:
            flash_message = f'error! {inst}'
        flash(flash_message)
        return redirect(url_for('main.companies'))
    return render_template('quick_form.html', title='Add Company', form=form)


@bp.route('/edit_company/<company_acronym>', methods=['GET', 'POST'])
@requires_access_level(ACCESS['admin'])
@login_required
def edit_company(company_acronym):
    company = Company.get_company_acronym(company_acronym)
    form = CompanyForm(request.form, obj=company)
    if form.validate_on_submit():
        form.populate_obj(company)
        flash_message = 'The company has been modified!'
        try:
            db.session.commit()
        except Exception as inst:
            flash_message = f'error! {inst}'
        flash(flash_message)
        return redirect(url_for('main.companies'))
    return render_template('quick_form.html', title='Edit Company', form=form)
