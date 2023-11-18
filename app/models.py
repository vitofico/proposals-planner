import base64
import calendar
import os
from datetime import datetime, timedelta
from hashlib import md5
from time import time

import jwt
from dateutil import tz
from dateutil.relativedelta import relativedelta
from flask import current_app, url_for
from flask_login import UserMixin
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy_continuum import make_versioned
from sqlalchemy_continuum.plugins import FlaskPlugin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login

ACCESS = {
    'guest': 0,
    'user': 1,
    'admin': 2,
    'superuser': 3
}

ROLES = {
    'read_only': 0,
    'edit': 1,
    'responsible': 2
}

date_format = '%Y-%m-%d'

make_versioned(plugins=[FlaskPlugin()])


class PaginatedAPIMixin(object):
    @staticmethod
    def to_collection_dict(query, page, per_page, endpoint, **kwargs):
        resources = query.paginate(page, per_page, False)
        data = {
            'items': [item.to_dict() for item in resources.items],
            '_meta': {
                'page': page,
                'per_page': per_page,
                'total_pages': resources.pages,
                'total_items': resources.total
            },
            '_links': {
                'self': url_for(endpoint, page=page, per_page=per_page,
                                **kwargs),
                'next': url_for(endpoint, page=page + 1, per_page=per_page,
                                **kwargs) if resources.has_next else None,
                'prev': url_for(endpoint, page=page - 1, per_page=per_page,
                                **kwargs) if resources.has_prev else None
            }
        }
        return data


class User(UserMixin, PaginatedAPIMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    name = db.Column(db.String(128))
    surname = db.Column(db.String(128))
    email = db.Column(db.String(128))
    password_hash = db.Column(db.String(128))
    access = db.Column(db.Integer)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    token = db.Column(db.String(32), index=True, unique=True)
    token_expiration = db.Column(db.DateTime)
    trello_token = db.Column(db.String(64))
    trello_api_key = db.Column(db.String(128))
    todos = db.relationship('ToDo', backref='ref_user', lazy='dynamic',
                            cascade='all, delete, delete-orphan')

    def __repr__(self):
        return '<{} {}>'.format(self.username, self.email)

    def is_superuser(self):
        return self.access == ACCESS['superuser']

    def allowed(self, access_level):
        return self.access >= access_level

    def proposal_role(self, proposal_acronym):
        proposal = Proposal.get_proposal_acronym(proposal_acronym)
        association = User_Proposal.query.filter_by(user=self, proposal=proposal).first()
        if association:
            return association.role
        else:
            return None

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.username.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'],
            algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    def get_token(self, expires_in=86400):
        now = datetime.utcnow()
        if self.token and self.token_expiration > now + timedelta(seconds=60):
            return self.token
        self.token = base64.b64encode(os.urandom(24)).decode('utf-8')
        self.token_expiration = now + timedelta(seconds=expires_in)
        db.session.add(self)
        db.session.commit()
        return self.token

    def revoke_token(self):
        self.token_expiration = datetime.utcnow() - timedelta(seconds=1)

    @staticmethod
    def check_token(token):
        user = User.query.filter_by(token=token).first()
        if user is None or user.token_expiration < datetime.utcnow():
            return None
        return user


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class ProposalStatus(db.Model):
    __tablename__ = 'proposalstatus'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(140), index=True, unique=True, nullable=False)
    description = db.Column(db.String(1024))
    badge_type = db.Column(db.String(140))

    def __repr__(self):
        return f'{self.status}'

    @classmethod
    def get_statuses(self):
        return [(x.status, x.status) for x in self.query.all()]

    @classmethod
    def get_status(cls, status_name):
        return cls.query.filter_by(status=status_name).first()


class Association(db.Model):
    __versioned__ = {}
    __tablename__ = 'association'
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposal.id'), primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), primary_key=True)
    participant_number = db.Column(db.Integer)
    personnel_cost = db.Column(db.Float)
    subcontracting_cost = db.Column(db.Float)
    other_direct_costs = db.Column(db.Float)
    proposal_related_text = db.Column(db.Text)
    is_coordinator = db.Column(db.Boolean)
    company = db.relationship('Company', backref='proposal_membership',
                              cascade='all, delete')
    proposal = db.relationship('Proposal', backref='proposal_participant',
                               cascade='all, delete')

    def __init__(self, proposal=None, company=None, personnel_cost=None, subcontracting_cost=None,
                 other_direct_costs=None, proposal_related_text=None, is_coordinator=False, participant_number=False):
        self.proposal = proposal
        self.company = company
        self.personnel_cost = personnel_cost
        self.subcontracting_cost = subcontracting_cost
        self.other_direct_costs = other_direct_costs
        self.remarks = proposal_related_text
        self.is_coordinator = is_coordinator
        self.participant_number = participant_number

    def __repr__(self):
        return f'<{self.proposal} {self.company} {self.personnel_cost}>'


class WP_Company(db.Model):
    __versioned__ = {}
    __tablename__ = 'wp_company'
    WP_id = db.Column(db.Integer, db.ForeignKey('wp.id'), primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), primary_key=True)
    person_month = db.Column(db.Float)
    leader = db.Column(db.Boolean)
    company = db.relationship('Company', backref='wp_membership',
                              cascade='all, delete')
    wp = db.relationship('WP', backref='company_participant',
                         cascade='all, delete')

    def __init__(self, wp=None, company=None, person_month=None, leader=False):
        self.wp = wp
        self.company = company
        self.person_month = person_month
        self.leader = leader

    def __repr__(self):
        return f'<{self.wp.number} {self.company.acronym} {self.person_month} {self.leader}>'


class User_Proposal(db.Model):
    __tablename__ = 'user_proposal'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposal.id'), primary_key=True)
    role = db.Column(db.Integer)
    proposal = db.relationship('Proposal', backref='user_membership',
                               cascade='all, delete')
    user = db.relationship('User', backref='proposal_user',
                           cascade='all, delete')

    def __init__(self, proposal=None, user=None, role=None):
        self.proposal = proposal
        self.user = user
        self.role = role

    def is_responsible(self):
        if self.role == ROLES['responsible']:
            return True
        else:
            return False

    def __repr__(self):
        return f'<{self.proposal} {self.user} {self.role}>'


class Proposal(PaginatedAPIMixin, db.Model):
    __versioned__ = {}
    __tablename__ = 'proposal'
    id = db.Column(db.Integer, primary_key=True)
    acronym = db.Column(db.String(64), index=True, unique=True, nullable=False)
    title = db.Column(db.String(256), nullable=False)
    participants = association_proxy("proposal_participant", "company")
    users = association_proxy("proposal_user", "proposal")
    description = db.Column(db.Text)
    budget = db.Column(db.Float)
    duration_months = db.Column(db.Integer)
    start_date = db.Column(db.Date)
    action_type = db.Column(db.String(512))
    indirect_costs_rate = db.Column(db.Float)
    call = db.Column(db.String(256))
    topic = db.Column(db.String(256))
    working_packages = db.relationship('WP', backref='ref_proposal', lazy='dynamic',
                                       cascade='all, delete, delete-orphan')
    status_id = db.Column(db.Integer, db.ForeignKey('proposalstatus.id'))
    status = db.relationship("ProposalStatus")
    todos = db.relationship('ToDo', backref='ref_proposal', lazy='dynamic',
                            cascade='all, delete, delete-orphan')

    def __repr__(self):
        return '<{}>'.format(self.acronym)

    def to_dict(self):
        data = {
            'id': self.id,
            'acronym': self.acronym,
            'title': self.title,
            'start_date': self.start_date.isoformat() + 'Z',
            'description': self.description,
            'budget': self.budget,
            'duration_months': self.duration_months,
            '_links': {
                'self': url_for('api.get_proposal', id=self.id)
            }
        }
        return data

    def add_participant(self, company, personnel_cost, subcontracting_cost, is_coordinator, other_direct_costs,
                        proposal_related_text, participant_number):
        if is_coordinator is True:
            association = Association.query.filter_by(proposal=self, is_coordinator=True).first()
            if association:
                association.is_coordinator = False
        if not self.is_included(company):
            association = Association(self, company, personnel_cost=personnel_cost, is_coordinator=is_coordinator,
                                      subcontracting_cost=subcontracting_cost, other_direct_costs=other_direct_costs,
                                      proposal_related_text=proposal_related_text,
                                      participant_number=participant_number)
            db.session.add(association)
            db.session.commit()
        else:
            association = Association.query.filter_by(company=company, proposal=self).first()
            association.personnel_cost = personnel_cost
            association.subcontracting_cost = subcontracting_cost
            association.other_direct_costs = other_direct_costs
            association.is_coordinator = is_coordinator
            association.proposal_related_text = proposal_related_text
            association.participant_number = participant_number
            db.session.commit()

    def remove_participant(self, company):
        if self.is_included(company):
            Association.query.filter_by(company=company, proposal=self).delete()
            for wp in self.working_packages:
                WP_Company.query.filter_by(company=company, wp=wp).delete()
            db.session.commit()

    def get_participant(self, company):
        return Association.query.filter_by(company=company, proposal=self).first()

    def is_included(self, company):
        return Association.query.filter_by(company=company, proposal=self).count() > 0

    def add_user(self, user, role):
        if not self.user_is_included(user):
            association = User_Proposal(user=user, proposal=self, role=role)
            db.session.add(association)
            db.session.commit()
        else:
            association = User_Proposal.query.filter_by(user=user, proposal=self).first()
            association.role = role
            db.session.commit()

    def remove_user(self, user):
        if self.user_is_included(user):
            User_Proposal.query.filter_by(user=user, proposal=self).delete()
            db.session.commit()

    def user_is_included(self, user):
        return User_Proposal.query.filter_by(user=user, proposal=self).count() > 0

    def update(self, data):
        self.acronym = data['acronym']
        self.title = data['title']
        self.description = data['description']
        self.budget = data['budget']
        self.indirect_costs_rate = int(data['indirect_costs_rate_percent']) / 100
        self.call = data['call']
        self.topic = data['topic']
        self.action_type = data['action_type']
        self.status = ProposalStatus.get_status(data['status'])
        self.start_date = datetime.strptime(data['start_date'], date_format)
        self.duration_months = data['duration_months']
        db.session.commit()

    def get_remaining_budget(self):
        assigned = [((x.personnel_cost + x.other_direct_costs) * (
                    1 + self.indirect_costs_rate) + x.subcontracting_cost) * x.proposal.get_reimbursement_rate(
            x.company, decimal=True)
                    for x
                    in self.proposal_participant]
        return self.budget - sum(assigned)

    def get_reimbursement_rate(self, company, decimal=False):
        if self.action_type == 'IA':
            if company.company_type == 'Large' or company.company_type == 'SME':
                if decimal:
                    return 0.7
                else:
                    return 70
        if decimal:
            return 1
        else:
            return 100

    def serialise_budget(self):
        data = [{'name': x.company.acronym,
                 'y': (x.personnel_cost + x.other_direct_costs) * (
                         1 + self.indirect_costs_rate) + x.subcontracting_cost,
                 'drilldown': x.company.acronym} for x in self.proposal_participant]
        # data.append({'name': 'Not Assigned', 'y': self.get_remaining_budget(), 'drilldown': 'null'})

        series_drilldown = list()
        for x in self.proposal_participant:
            a = ['Personnel Cost', x.personnel_cost]
            b = ['Other Direct Cost', x.other_direct_costs]
            c = ['Subcontracting Cost', x.subcontracting_cost]
            d = ['Indirect Cost', (x.personnel_cost + x.other_direct_costs) * self.indirect_costs_rate]
            name = x.company.acronym
            id = x.company.acronym
            series_drilldown.append({'name': name, 'id': id, 'data': [a, b, c, d]})

        series = [{'name': 'Budget Shares', 'data': data}]

        return series, series_drilldown

    def get_gantt_data(self):
        data = [{'name': f'WP{x.number} - {x.title}', 'id': f'{x.number}',
                 'start': self.start_date + relativedelta(months=x.start_month),
                 'end': self.start_date + relativedelta(months=x.end_month)} for x in self.working_packages]

        for wp in self.working_packages:
            for deliverable in wp.deliverables:
                data.append({'name': f'D{wp.number}.{deliverable.number} - {deliverable.title}',
                             'id': f'{wp.number}.{deliverable.number}',
                             'start': self.start_date + relativedelta(months=deliverable.due_month),
                             'end': self.start_date + relativedelta(months=deliverable.due_month + 1),
                             'responsible': deliverable.responsible, 'milestone': 'true', 'parent': f'{wp.number}'})

        for element in data:
            element['start'] = datetime.combine(element['start'], datetime.min.time())
            element['start'] = (calendar.timegm(element['start'].astimezone(tz.UTC).utctimetuple())) * 1000
            element['end'] = datetime.combine(element['end'], datetime.min.time())
            element['end'] = (calendar.timegm(element['end'].astimezone(tz.UTC).utctimetuple())) * 1000
            # element['start'] = f'Date.UTC({element["start"].year},{element["start"].month},{element["start"].day})'
            # element['end'] = f'Date.UTC({element["end"].year},{element["end"].month},{element["end"].day})'
        series = [{'name': f'{self.acronym}', 'data': data}]
        return series

    def get_map_data(self):
        d=dict()
        for x in self.proposal_participant:
            country=f'{x.company.country}'.lower().replace('uk','gb')
            if country in d:
                d[country].append(f'{x.company.acronym}')
            else:
                d[country] = [f'{x.company.acronym}']
        data = [[key, '<br>'.join(value)] for key, value in d.items()]

        dataLabels = {'enabled': 'true', 'color': "#FFFFFF"}
        tooltip = {'pointFormat': '{point.name}', 'headerFormat': ''}
        series = [{'name': 'Country', 'data': data, 'dataLabels' : dataLabels, 'tooltip': tooltip}]
        return series

    @classmethod
    def get_proposals(cls):
        return cls.query.all()

    @classmethod
    def get_proposal_acronym(cls, acronym):
        return cls.query.filter_by(acronym=acronym).first()

    @classmethod
    def get_topics_list(cls):
        return list(set([x.topic for x in cls.query.all()]))

    @classmethod
    def get_calls_list(cls):
        return list(set([x.call for x in cls.query.all()]))


class Company(db.Model):
    __tablename__ = 'company'
    id = db.Column(db.Integer, primary_key=True)
    acronym = db.Column(db.String(64), index=True, unique=True, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text)
    country = db.Column(db.String(64), index=True)
    contact_email = db.Column(db.String(120), unique=True)
    company_type = db.Column(db.String(256))
    specialisation = db.Column(db.String(256))
    pic = db.Column(db.String(256), unique=True)
    memberships = association_proxy("proposal_membership", "proposal")

    def __repr__(self):
        return '<{}>'.format(self.acronym)

    @classmethod
    def get_companies(cls):
        return [(x.acronym, x.name) for x in Company.query.order_by(Company.name).all()]

    @classmethod
    def get_company_id(cls, id):
        return cls.query.get(id)

    @classmethod
    def get_company_acronym(cls, acronym):
        return cls.query.filter_by(acronym=acronym).first()


class WP(db.Model):
    __versioned__ = {}
    __tablename__ = 'wp'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text)
    start_month = db.Column(db.Integer)
    end_month = db.Column(db.Integer)
    proposal_reference = db.Column(db.Integer, db.ForeignKey('proposal.id'))
    participants = association_proxy("company_participant", "company")
    deliverables = db.relationship('Deliverable', backref='ref_wp', lazy='dynamic',
                                   cascade='all, delete, delete-orphan')
    milestones = db.relationship('Milestone', backref='ref_wp', lazy='dynamic',
                                 cascade='all, delete, delete-orphan')

    def __repr__(self):
        return f'<{self.proposal_reference} WP{self.number} >'

    def to_dict(self):
        data = {
            'id': self.id,
            'number': self.number,
            'title': self.title,
            'description': self.description,
            'start_month': self.start_month,
            'end_month': self.end_month,
        }
        return data

    @classmethod
    def get_wp(cls, proposal, number):
        return cls.query.filter_by(ref_proposal=proposal, number=number).first()

    def is_included(self, company):
        return WP_Company.query.filter_by(company=company, wp=self).count() > 0

    def add_participant(self, company, person_month, leader=False):
        if leader is True:
            association = WP_Company.query.filter_by(wp=self, leader=True).first()
            if association:
                association.leader = False
        if not self.is_included(company):
            association = WP_Company(self, company, person_month=person_month, leader=leader)
            db.session.add(association)
            db.session.commit()
        else:
            association = WP_Company.query.filter_by(company=company, wp=self).first()
            association.person_month = person_month
            association.leader = leader
            db.session.commit()

    def get_leader_acronym(self):
        association = WP_Company.query.filter_by(wp=self, leader=True).first()
        if association:
            return association.company.acronym
        else:
            return None

    def remove_participant(self, company):
        if self.is_included(company):
            WP_Company.query.filter_by(company=company, wp=self).delete()
            db.session.commit()

    def get_participant(self, company):
        return WP_Company.query.filter_by(company=company, wp=self).first()

    def get_participants(self):
        return [(x.company.acronym, x.company.name) for x in WP_Company.query.filter_by(wp=self).all()]

    def get_total_effort(self):
        data = [x.person_month for x in self.company_participant]
        return sum(data)

    def serialise_pm(self):
        data = [{'name': x.company.acronym, 'y': x.person_month} for x in self.company_participant]
        series = [{'name': 'PM Distribution', 'data': data}]
        return series


class Deliverable(db.Model):
    __versioned__ = {}
    __tablename__ = 'deliverable'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(256), nullable=False)
    responsible = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text)
    due_month = db.Column(db.Integer)
    type = db.Column(db.String(256))
    dissemination_level = db.Column(db.String(256))
    wp_reference = db.Column(db.Integer, db.ForeignKey('wp.id'))

    def __repr__(self):
        return f'<{self.wp_reference} D{self.number} >'

    def get_proposal_acronym(self):
        wp = self.ref_wp
        proposal = wp.ref_proposal
        return proposal.acronym

    @classmethod
    def get_bynumber(cls, wp, number):
        return cls.query.filter_by(ref_wp=wp, number=number).first()


class Milestone(db.Model):
    __versioned__ = {}
    __tablename__ = 'milestone'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(256), nullable=False)
    responsible = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text)
    due_month = db.Column(db.Integer)
    wp_reference = db.Column(db.Integer, db.ForeignKey('wp.id'))

    def __repr__(self):
        return f'<{self.wp_reference} M{self.number} >'

    def get_proposal_acronym(self):
        wp = self.ref_wp
        proposal = wp.ref_proposal
        return proposal.acronym

    @classmethod
    def get_bynumber(cls, wp, number):
        return cls.query.filter_by(ref_wp=wp, number=number).first()


class ToDo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    description = db.Column(db.Text)
    status = db.Column(db.String(128))
    due_date = db.Column(db.Date)
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)
    proposal_reference = db.Column(db.Integer, db.ForeignKey('proposal.id'))


db.configure_mappers()
