from flask import render_template, redirect, request, url_for, flash, Response
from flask_login import login_required

from app import db
from app.main import bp
from app.main.forms import UserTrelloTokenForm
from app.models import User


# User Panel

@bp.route("/<username>", methods=['GET', 'POST'])
@login_required
def user_panel(username):
    user = User.query.filter_by(username=username).first()
    form = UserTrelloTokenForm(obj=user)
    if form.validate_on_submit():
        data = request.form.to_dict()
        user.trello_api_key = data['trello_api_key']
        user.trello_token = data['trello_token']
        db.session.commit()
        flash_message = 'The Trello token has been correctly updated!'
        flash(flash_message)
        return redirect(url_for('main.user_panel', username=user.username))
    return render_template('user.html', form=form)
