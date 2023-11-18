from datetime import date

from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from wtforms import StringField, SubmitField, TextAreaField, SelectField, IntegerField, FloatField, BooleanField, \
    FileField
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, NumberRange, Email, ValidationError
from wtforms_alchemy import model_form_factory

from app import db
from app.models import ProposalStatus, Company, date_format, ROLES, User, User_Proposal

from country_list import countries_for_language

BaseModelForm = model_form_factory(FlaskForm)

DISSEMINATION_LEVELS = [('PU', 'Public'), ('PP', 'Restricted to other programme participants'),
                        ('RE', 'Restricted to a group specified by the consortium'),
                        ('CO', 'Confidential, only for members of the consortium'),
                        ('CL restraint UE', 'Classified with the mention of the classification level RESTREINT UE'),
                        ('CL confidential UE',
                         'Classified with the mention of the classification level CONFIDENTIEL UE'),
                        ('CL secret UE', 'Classified with the mention of the classification level SECRET UE')]

DELIVERABLE_TYPES = [('R', 'Document, Report'), ('DEM', 'Demonstrator, Pilot, Prototype, Plan designs'),
                     ('DEC', 'Websites, Patents filing, Press and media actions, Videos, etc.'),
                     ('OTHER', 'Software, Technical diagram, etc.')]

COMPANY_TYPES = [('RTO', 'Research and Technology Organization'), ('SME', 'Micro, Small and Medium-sized Enterprises'),
                 ('Large', 'Large Company'), ('University', 'University')]

PROPOSAL_TYPES = [('RIA', 'Research and Innovation Action'), ('IA', 'Innovation Action'),
                  ('CSA', 'Coordination and Support Action')]

TODO_STATUSES = [('Open', 'Open'), ('Closed', 'Closed')]

class ModelForm(BaseModelForm):
    @classmethod
    def get_session(self):
        return db.session


class CompanyForm(FlaskForm):
    acronym = StringField('Acronym', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    country = SelectField('Country', choices=(countries_for_language('en')))
    contact_email = StringField('Contact e-mail', validators=[Email()])
    company_type = SelectField('Company Type', choices=COMPANY_TYPES, validators=[DataRequired()])
    specialisation = StringField('Specialisation/Tags', description='Several inputs admitted, separated by semi-colon')
    pic = StringField('PIC number')
    submit = SubmitField(_l('Submit'))


class WPForm(ModelForm):
    number = IntegerField('Number', validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', id='description')
    start_month = SelectField('Start Month', validators=[DataRequired()])
    end_month = SelectField('End Month', validators=[DataRequired()])  # duration in months
    submit = SubmitField(_l('Submit'))

    def validate_end_month(form, field):
        if int(field.data) < int(form.start_month.data):
            raise ValidationError('a WP is not a time machine!')

    @classmethod
    def new(cls, obj, proposal):
        # Instantiate the form
        form = cls(obj=obj)

        # Update the choices for the participant field
        form.start_month.choices = [(f'{x}', x) for x in range(proposal.duration_months + 1)]
        form.end_month.choices = [(f'{x}', x) for x in range(proposal.duration_months + 1)]

        return form


class ProposalForm(FlaskForm):
    acronym = StringField('Acronym', validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Abstract', id='description')
    budget = FloatField('Budget (k€)', validators=[NumberRange(min=0), DataRequired()])
    duration_months = IntegerField('Duration (months)',
                                   validators=[NumberRange(min=0), DataRequired()])  # duration in months
    start_date = DateField('Start Date', format=date_format, validators=[DataRequired()])
    indirect_costs_rate_percent = IntegerField('Indirect Costs Rate (%)',
                                               validators=[NumberRange(min=0, max=100), DataRequired()], default=25)
    call = StringField('Call', id='call', validators=[DataRequired()])
    topic = StringField('Topic', id='topic', validators=[DataRequired()])
    action_type = SelectField('Action Type', choices=PROPOSAL_TYPES, validators=[DataRequired()])
    # status = SelectField ('Status', choices=ProposalStatus.get_statuses (), validators=[DataRequired ()])
    status = SelectField('Status', validators=[DataRequired()])
    submit = SubmitField(_l('Submit'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.start_date.data:
            self.start_date.data = date.today()
        self.status.choices = ProposalStatus.get_statuses()


class ParticipantForm(FlaskForm):
    participant = SelectField('Participant', validators=[DataRequired()])
    participant_number = IntegerField('Participant Number', validators=[DataRequired(), NumberRange(min=0)])
    personnel_cost = FloatField('Personnel Cost (k€)', validators=[NumberRange(min=0)])
    subcontracting_cost = FloatField('Subcontracting Cost (k€)', validators=[NumberRange(min=0)])
    other_direct_costs = FloatField('Other Direct Costs (k€)', validators=[NumberRange(min=0)])
    proposal_related_text = TextAreaField('Additional text for the proposal',
                                          description='- Description of the main tasks of the partner organisation in the project<br>'
                                                      '- Description of the main personnel profiles<br>'
                                                      '- List of relevant publications, and/or products, services or other achievements<br>'
                                                      '- List of previous related projects or activities<br>'
                                                      '- List of significant infrastructure')
    is_coordinator = BooleanField('Coordinator')
    submit = SubmitField(_l('Submit'))

    def __call__(self, field, **kwargs):
        return super(ParticipantForm, self).__call__(field, **kwargs)

    @classmethod
    def new(cls, obj, company=None):
        # Instantiate the form
        form = cls(obj=obj)
        if company:
            form.participant.choices = [(company.acronym, company.name)]
        else:
            # Update the choices for the agency field
            form.participant.choices = Company.get_companies()
        return form


class DeliverableForm(FlaskForm):
    responsible = SelectField('Responsible', validators=[DataRequired()])
    number = IntegerField('Number', validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Abstract', id='description')
    due_month = SelectField('Due Month', validators=[DataRequired()])
    type = SelectField('Type', choices=DELIVERABLE_TYPES, validators=[DataRequired()])
    dissemination_level = SelectField('Dissemination Level', choices=DISSEMINATION_LEVELS)
    submit = SubmitField(_l('Submit'))

    @classmethod
    def new(cls, obj, wp):
        # Instantiate the form
        form = cls(obj=obj)

        # Update the choices for the agency field
        form.responsible.choices = wp.get_participants()
        form.due_month.choices = [(f'{x}', x) for x in range(wp.start_month, wp.end_month + 1)]
        return form


class MilestoneForm(FlaskForm):
    responsible = SelectField('Responsible', validators=[DataRequired()])
    number = IntegerField('Number', validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Abstract', id='description')
    due_month = SelectField('Due Month', validators=[DataRequired()])
    submit = SubmitField(_l('Submit'))

    @classmethod
    def new(cls, obj, wp):
        # Instantiate the form
        form = cls(obj=obj)

        # Update the choices for the agency field
        form.responsible.choices = wp.get_participants()
        form.due_month.choices = [(f'{x}', x) for x in range(wp.start_month, wp.end_month + 1)]
        return form


class WPParticipantForm(FlaskForm):
    participant = SelectField('Participant', validators=[DataRequired()])
    person_month = FloatField('Effort (PM)', validators=[DataRequired()])
    leader = BooleanField('Leader')
    submit = SubmitField(_l('Submit'))

    @classmethod
    def new(cls, obj, proposal, company=None):
        # Instantiate the form
        form = cls(obj=obj)
        if company:
            # Update the choices for the participant field
            form.participant.choices = [(company.acronym, company.name)]
        else:
            form.participant.choices = sorted([(x.acronym, x.name) for x in proposal.participants], key=lambda tup: tup[1])
        return form


class UserPermissionForm(FlaskForm):
    user = SelectField('User', validators=[DataRequired()])
    role = SelectField('Role', choices=[(str(v), k) for k, v in ROLES.items()], validators=[DataRequired()])
    submit = SubmitField(_l('Submit'))

    @classmethod
    def new(cls):
        form = cls()

        form.user.choices = [(x.username, f'{x.name} {x.surname}') for x in User.query.all()]
        return form

class UserTrelloTokenForm(FlaskForm):
    trello_token = StringField('Trello Token', validators=[DataRequired()])
    trello_api_key = StringField('Trello API key', validators=[DataRequired()])
    submit = SubmitField(_l('Submit'))

## example for dynamic form creation
# general = {'Part Number': StringField ('Part Number', validators=[DataRequired ()]),
#              'Part Name': StringField ('Part Name', validators=[DataRequired ()]),
#              'Description': StringField ('Description', validators=[DataRequired ()]),
#              'Manufacturer': StringField ('Manufacturer', validators=[DataRequired ()])}
#
# def create_dynamic_form(d):
#     return type('DynamicForm', (FlaskForm, ), {**general, **d, 'submit' : SubmitField ('Save')})

class UploadForm(FlaskForm):
    submitted_file = FileField('File', validators=[FileRequired()])
    submit = SubmitField('Submit')


class ToDoForm(FlaskForm):
    assigned_to = SelectField('Assignee', validators=[DataRequired()])
    description = TextAreaField('Abstract', id='description')
    status = SelectField('Status', choices=TODO_STATUSES, validators=[DataRequired()])
    due_date = DateField('Due Date', format=date_format, validators=[DataRequired()])
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.due_date.data:
            self.due_date.data = date.today()
        self.assigned_to.choices = [(f"{x.user.username}", f"{x.user.name} {x.user.surname}") for x in User_Proposal.query.filter_by(proposal=kwargs['proposal']).all()]