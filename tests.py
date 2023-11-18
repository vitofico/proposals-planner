#!/usr/bin/env python
from datetime import datetime, timedelta
import unittest
from app import create_app, db
from app.models import User, Proposal, Company, WP, Deliverable, Milestone
from config import Config

import lorem


class TestConfig(Config):
    TESTING = True
    ELASTICSEARCH_URL = None


class UserModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        # db.drop_all()
        self.app_context.pop()

    def test_password_hashing(self):
        u = User(username='vito')
        u.set_password('nous')
        self.assertFalse(u.check_password('dog'))
        self.assertTrue(u.check_password('nous'))


class ComponentModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        # db.drop_all()
        self.app_context.pop()

    def test_addproposal(self):
        u1 = Proposal(acronym='VICTIM', title='Visual hIerarchical ClusTering usIng k-Means',
                      description=lorem.text(), budget=85.3, action_type='IA', call='HEU', topic='LC-TT-3-51',
                      start_date=datetime.today(), duration_months=24, indirect_costs_rate=0.25)

        u2 = Proposal(acronym='ABBOT', title='Africa Blue BOTtles',
                      description="Mangled thighs have been turning up all over Devon and the inhabitants are scared. Ten murders in ten weeks, all committed with a spoon, and still nobody has a clue who the creepy killer is. DCI Jenna Clifford is a puny and witty teacher with a fondness for music. She doesn't know it yet but she is the only one who can stop the stingy killer. When her wife, Ruth Torrance, is kidnapped, DCI Clifford finds herself thrown into the centre of the investigation. His only clue is a ribbed banana. She enlists the help of an optimistic shopkeeper called Will Connor. Can Connor help Clifford overcome her caffeine addiction and find the answers before the clumsy killer and his deadly spoon strike again?",
                      budget=79.8, action_type='CSA', call='HEU', topic='LC-DG-9-11',
                      start_date=datetime.today(), duration_months=48, indirect_costs_rate=0.25)

        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()

        # create company users
        a1 = Company(acronym='COPER', name='Capable Of Producing EveRything', description=lorem.paragraph(),
                     country='UK', company_type='SME', specialisation='Post Moore Processors')
        a2 = Company(acronym='NUB', name='UnusualBadass', description=lorem.paragraph(), country='IT',
                     company_type='Large', specialisation='Ads')
        a3 = Company(acronym='RFD', name='Rich Fat Dog', description=lorem.paragraph(), country='US',
                     company_type='RTO', specialisation='Canine; Rich; Morbid')

        for a in [a1, a2, a3]:
            db.session.add(a)
        db.session.commit()

        u1.add_participant(Company.get_company_acronym(a1.acronym), personnel_cost=50, subcontracting_cost=22,
                           other_direct_costs=0, is_coordinator=True, proposal_related_text='', participant_number=1)

        u2.add_participant(Company.get_company_acronym(a2.acronym), personnel_cost=21.5, subcontracting_cost=2,
                           other_direct_costs=11, is_coordinator=True, proposal_related_text='', participant_number=2)

        w1 = WP(number=1, title='Study of a normal distributed curve', description=lorem.text(), start_month=2,
                end_month=5)
        w2 = WP(number=2, title='Normally Doing Nothing', description=lorem.text(), start_month=0,
                end_month=21)
        w3 = WP(number=1, title='Saving bottles in Africa', description=lorem.text(), start_month=0,
                end_month=4)

        d1 = Deliverable(number=1, title='Distributed curve', description=lorem.text(), due_month=5,
                         responsible='COPER')
        d2 = Deliverable(number=1, title='Delivering Nothing', description=lorem.text(), due_month=20,
                         responsible='COPER')

        m1 = Milestone(number=1, title='KoM', description=lorem.text(), due_month=5, responsible='COPER')
        m2 = Milestone(number=2, title='PDR', description=lorem.text(), due_month=20, responsible='COPER')

        u1.working_packages.append(w1)
        u1.working_packages.append(w2)

        u2.working_packages.append(w3)

        w1.deliverables.append(d1)
        w2.deliverables.append(d2)
        w1.milestones.append(m1)
        w2.milestones.append(m2)
        w3.milestones.append(m1)

        self.assertEqual(u1.query.count(), 2)
        self.assertEqual(w1.query.count(), 3)
        self.assertEqual(a1.query.count(), 3)

        db.session.commit()


if __name__ == '__main__':
    unittest.main(verbosity=2)
