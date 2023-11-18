# import things
import re

from flask_table import Table, Col, LinkCol, create_table, BoolCol

from app.models import Proposal

# Declare your table


class WPTable(Table):
    number = Col('#')
    title = LinkCol('Title', 'main.wp_dashboard',
                    url_kwargs=dict(proposal_acronym='proposal.acronym', wp_number='wp.number'), attr='title')
    lead_participant = Col('Leader')
    person_month = Col('Total PM')
    start_month = Col('Start Month')
    end_month = Col('End Month')
    # delete_wp = LinkCol ('Remove', 'main.remove_wp', url_kwargs=dict (proposal_acronym='proposal.acronym', wp_number='wp.number'), text_fallback='&times;')
    # table_id = 'wp_table'
    classes = ['display']


def get_WP_table(proposal_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    items = []
    for wp in proposal.working_packages:
        items.append(dict(number=wp.number, title=wp.title, lead_participant=wp.get_leader_acronym(),
                          person_month=wp.get_total_effort(), start_month=wp.start_month,
                          end_month=wp.end_month, proposal=proposal, wp=wp))

    return WPTable(items)


class BudgetTable(Table):
    participant_number = Col('Participant Number')
    participant = Col('Participant Acronym')
    country = Col('Country')
    personnel_costs = Col('Personnel Costs (k€)')
    other_direct_costs = Col('Other Direct Costs (k€)')
    subcontracting_costs = Col('Subcontracting Costs (k€)')
    indirect_costs = Col('Indirect Costs (k€)')
    total_costs = Col('Total Costs (k€)')
    reimbursement_rate = Col('Reimbursement Rate (%)')
    contribution = Col('Contribution (k€)')
    # table_id = 'budget_table'
    classes = ['display']
    # html_attrs = {'style':"width: 100%;", 'border':"1"}


def get_budget_table(proposal_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    items = []
    indirect_costs_rate = proposal.indirect_costs_rate
    for element in proposal.proposal_participant:
        reimbursement_rate_percent = proposal.get_reimbursement_rate(element.company)
        indirect_costs = (element.personnel_cost + element.other_direct_costs) * indirect_costs_rate
        total_costs = element.personnel_cost + element.other_direct_costs + indirect_costs + element.subcontracting_cost
        items.append(dict(participant_number=element.participant_number, participant=element.company.acronym,
                          country=element.company.country, personnel_costs=element.personnel_cost,
                          other_direct_costs=element.other_direct_costs,
                          subcontracting_costs=element.subcontracting_cost,
                          indirect_costs=indirect_costs, total_costs=total_costs,
                          reimbursement_rate=reimbursement_rate_percent,
                          contribution=total_costs * reimbursement_rate_percent / 100))
    return BudgetTable(items)


def get_WPeffort_table(proposal_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)

    tbl_options = dict(table_id='wp_effort_table', classes=['display'])

    TableCls = create_table('TableCls', options=tbl_options).add_column('wp', LinkCol('WP no.', 'main.wp_dashboard',
                                                                                      url_kwargs=dict(
                                                                                          proposal_acronym='proposal_acronym',
                                                                                          wp_number='wp_number'),
                                                                                      attr='wp'))

    for company in proposal.participants:
        TableCls.add_column(f'{company.acronym}', Col(f'{company.acronym}'))

    TableCls.add_column('sum_wp', Col('Total'))

    items = []
    for wp in proposal.working_packages:
        d = {company.acronym: None for company in proposal.participants}
        d["wp"] = wp.number
        d["proposal_acronym"] = proposal.acronym
        d["wp_number"] = wp.number
        sum = 0;
        for item in wp.company_participant:
            d[item.company.acronym] = item.person_month
            sum += item.person_month
        d['sum_wp'] = sum
        items.append(d)

    return TableCls(items)


class DeliverableTable(Table):
    del_number = LinkCol('', 'main.edit_WP_deliverable',
                         url_kwargs=dict(proposal_acronym='proposal_acronym', wp_number='wp_number',
                                         deliverable_number='number'), attr='del_number')
    title = Col('Title')
    responsible = Col('Responsible')
    description = Col('Description')
    due_month = Col('Due Month')
    type = Col('Type')
    dissemination_level = Col('Dissemination Level')
    remove = LinkCol('', 'main.remove_WP_deliverable',
                     url_kwargs=dict(proposal_acronym='proposal_acronym', wp_number='wp_number',
                                     deliverable_number='number'), text_fallback='Remove')
    # table_id = 'deliverable_table'
    classes = ['display']


def get_wp_deliverable_table(wp_object):
    proposal = wp_object.ref_proposal
    items = []
    for deliverable in wp_object.deliverables:
        items.append(dict(proposal_acronym=proposal.acronym, wp_number=wp_object.number,
                          responsible=deliverable.responsible, title=deliverable.title,
                          description=deliverable.description, due_month=deliverable.due_month,
                          type=deliverable.type, number=deliverable.number,
                          del_number=f'D{wp_object.number}.{deliverable.number}',
                          dissemination_level=deliverable.dissemination_level))
    return DeliverableTable(items)


def get_proposal_deliverable_table(proposal_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    items = []
    for wp in proposal.working_packages:
        for deliverable in wp.deliverables:
            items.append(dict(proposal_acronym=proposal.acronym, wp_number=wp.number,
                              responsible=deliverable.responsible, title=deliverable.title,
                              description=deliverable.description, due_month=deliverable.due_month,
                              type=deliverable.type, number=deliverable.number,
                              del_number=f'D{wp.number}.{deliverable.number}',
                              dissemination_level=deliverable.dissemination_level))
    return DeliverableTable(items)


class MilestoneTable(Table):
    mil_number = LinkCol('', 'main.edit_WP_milestone',
                         url_kwargs=dict(proposal_acronym='proposal_acronym', wp_number='wp_number',
                                         milestone_number='number'), attr='mil_number')
    title = Col('Title')
    responsible = Col('Responsible')
    description = Col('Description')
    due_month = Col('Due Month')
    remove = LinkCol('', 'main.remove_WP_milestone',
                     url_kwargs=dict(proposal_acronym='proposal_acronym', wp_number='wp_number',
                                     milestone_number='number'), text_fallback='Remove')
    # table_id = 'deliverable_table'
    classes = ['display']


def get_wp_milestone_table(wp_object):
    proposal = wp_object.ref_proposal
    items = []
    for milestone in wp_object.milestones:
        items.append(dict(proposal_acronym=proposal.acronym, wp_number=wp_object.number,
                          responsible=milestone.responsible, title=milestone.title,
                          description=milestone.description, due_month=milestone.due_month,
                          number=milestone.number, mil_number=f'M{milestone.number}'))
    return MilestoneTable(items)


def get_proposal_milestone_table(proposal_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    items = []
    for wp in proposal.working_packages:
        for milestone in wp.milestones:
            items.append(dict(proposal_acronym=proposal.acronym, wp_number=wp.number,
                              responsible=milestone.responsible, title=milestone.title,
                              description=milestone.description, due_month=milestone.due_month,
                              number=milestone.number, mil_number=f'M{milestone.number}'))

    return MilestoneTable(items)


class ParticipantsTable(Table):
    acronym = Col('Participant Acronym')
    name = Col('Participant Name')
    country = Col('Country')
    role = BoolCol('Coordinator')
    classes = ['display']


def get_participants_table(proposal_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    items = []
    for element in proposal.proposal_participant:
        items.append(dict(acronym=element.company.acronym, country=element.company.country,
                          name=element.company.name, role=element.is_coordinator))
    return ParticipantsTable(items)


def inject_footer(table_html):
    m = re.search('<thead>(.*)</thead>', table_html)
    res = re.sub('<th>(.*?)</th>', '<th></th>', m.group(1))
    return table_html.replace('</table>', f'<tfoot>{res}</tfoot> </table>')
