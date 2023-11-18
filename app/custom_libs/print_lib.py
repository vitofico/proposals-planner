# import things
import os

from flask_table import create_table, Col, Table

from app.main.forms import DISSEMINATION_LEVELS, DELIVERABLE_TYPES
from app.models import Proposal, Company
from app.custom_libs.tables_lib import get_WP_table, get_WPeffort_table, get_participants_table
from app.custom_libs.utilities_lib import create_folder


class ProposalText:
    def __init__(self, proposal):
        self.proposal = proposal
        self.folder = create_folder(self.proposal.acronym)

    def define_path(self, filename):
        return os.path.join(self.folder, filename)

    def general_info(self):
        return f""" {to_hx('General Information', 1)}\n
{wrap_with(wrap_with('Call: ', 'b') + self.proposal.call, 'p')}\n
{wrap_with(wrap_with('Acronym: ', 'b') + self.proposal.acronym, 'p')}\n
{wrap_with(wrap_with('Title: ', 'b') + self.proposal.title, 'p')}\n
{wrap_with(wrap_with('Duration in months: ', 'b') + str(self.proposal.duration_months), 'p')}\n
{wrap_with(wrap_with('Abstract: ', 'b') + self.proposal.description, 'p')}"""

    def participants(self):
        table = get_participants_table(self.proposal.acronym)
        return f""" {to_hx('Participants', 1)}\n{table.__html__()}"""

    def budget(self):
        table = get_printable_budget_table(self.proposal.acronym)
        return f""" {to_hx('Budget', 1)}\n{wrap_with('All the costs are in kEUR', 'p')}\n{table.__html__()}"""

    def wp_list(self):
        table = get_WP_table(self.proposal.acronym)
        return f""" {to_hx('Working Packages List', 1)}\n{table.__html__()}"""

    def efforts(self):
        table = get_WPeffort_table(self.proposal.acronym)
        return f""" {to_hx('Effort per WP', 1)}\n{table.__html__()}"""

    def deliverables(self):
        table = get_printable_deliverable_table(self.proposal.acronym)
        return f""" {to_hx('Deliverables', 1)}\n{table.__html__()}"""

    def write_description(self):
        with open(f'{self.define_path(self.proposal.acronym)}.html', 'w+') as file:
            file.write(self.general_info())
            file.write(self.participants())
            file.write(self.budget())
            file.write(self.wp_list())
            file.write(self.efforts())
            file.write(self.deliverables())

            for wp in self.proposal.working_packages:
                file.write(to_hx(f'WP{wp.number} - {wp.title}', 2))
                file.write(wp_summary(wp))
                file.write(wrap_with(f"{wrap_with('Description:', 'b')} {wp.description}", 'p'))
                file.write(
                    wrap_with(f"{wrap_with('Deliverables:', 'b')} {get_printable_wp_deliverable_table(wp).__html__()}",
                              'p'))
                for deliverable in wp.deliverables:
                    file.write(wp_deliverables(deliverable))

        return f'{self.define_path(self.proposal.acronym)}.html'


def to_hx(text, level):
    return f"<h{level}> {text} </h{level}>\n"


def wrap_with(text, tag='div'):
    return f"<{tag}> {text} </{tag}>\n"


def wp_summary(wp):
    str1 = wrap_with(
        f"{wrap_with('Start Month:', 'b')} {wp.start_month} - {wrap_with('End Month:', 'b')} {wp.end_month}", 'p')
    if wp.get_leader_acronym():
        str2 = wrap_with(f"{wrap_with('Lead Beneficiary:', 'b')} {Company.get_company_acronym(wp.get_leader_acronym()).name}", 'p')
    else:
        str2 = wrap_with(
            f"{wrap_with('Lead Beneficiary:', 'b')} Not Assigned", 'p')
    tab = get_wp_effort_summary_table(wp)
    str3 = wrap_with(tab.__html__(), 'div')
    return str1 + str2 + str3


def wp_deliverables(deliverable):
    str = to_hx(f'D{deliverable.ref_wp.number}.{deliverable.number} - {deliverable.title}', 3)
    str1 = wrap_with(f"{wrap_with('Due Month:', 'b')} {deliverable.due_month}", 'p')
    str2 = wrap_with(f"{wrap_with('Responsible:', 'b')} {Company.get_company_acronym(deliverable.responsible).name}", 'p')
    type = [item[1] for item in DELIVERABLE_TYPES if item[0] == deliverable.type][0]
    str3 = wrap_with(f"{wrap_with('Type:', 'b')} {type}", 'p')
    diss_lev = [item[1] for item in DISSEMINATION_LEVELS if item[0] == deliverable.dissemination_level][0]
    str4 = wrap_with(f"{wrap_with('Dissemination Level:', 'b')} {diss_lev}", 'p')
    str5 = wrap_with(f"{wrap_with('Description:', 'b')} {deliverable.description}", 'p')
    return str + str1 + str2 + str3 + str4 + str5


# Printable Tables

def get_wp_effort_summary_table(wp):
    TableCls = create_table('TableCls').add_column('wp', Col(''))
    proposal = wp.ref_proposal

    for company in proposal.participants:
        TableCls.add_column(f'{company.acronym}', Col(f'{company.acronym}'))

    TableCls.add_column('sum_wp', Col('Total'))

    items = []

    d = {company.acronym: None for company in proposal.participants}
    d["wp"] = f"WP{wp.number}"
    d["proposal_acronym"] = proposal.acronym
    d["wp_number"] = wp.number
    sum = 0;
    for item in wp.company_participant:
        d[item.company.acronym] = item.person_month
        sum += item.person_month
    d['sum_wp'] = sum
    items.append(d)

    return TableCls(items)


class BudgetTablePrintable(Table):
    participant = Col('')
    personnel_costs = Col('Personnel')
    other_direct_costs = Col('Other Costs')
    subcontracting_costs = Col('Subcontr.')
    indirect_costs = Col('Indirect')
    total_costs = Col('Total')
    reimbursement_rate = Col('Rate (%)')
    contribution = Col('Contribution')
    table_id = 'budget_table'


def get_printable_budget_table(proposal_acronym):
    proposal = Proposal.get_proposal_acronym(proposal_acronym)
    items = []
    indirect_costs_rate = proposal.indirect_costs_rate
    for element in proposal.proposal_participant:
        indirect_costs = (element.personnel_cost + element.other_direct_costs) * indirect_costs_rate
        total_costs = element.personnel_cost + element.other_direct_costs + indirect_costs + element.subcontracting_cost
        reimbursement_rate_percent = proposal.get_reimbursement_rate(element.company)
        items.append(dict(participant=element.company.acronym, country=element.company.country,
                          personnel_costs=element.personnel_cost,
                          other_direct_costs=element.other_direct_costs,
                          subcontracting_costs=element.subcontracting_cost,
                          indirect_costs=indirect_costs, total_costs=total_costs,
                          reimbursement_rate=reimbursement_rate_percent,
                          contribution=total_costs * reimbursement_rate_percent / 100))
    return BudgetTablePrintable(items)


class DeliverableTablePrintable(Table):
    del_number = Col('#')
    title = Col('Title')
    responsible = Col('Responsible')
    due_month = Col('Due Month')
    type = Col('Type')
    dissemination_level = Col('Level')
    table_id = 'deliverable_table'


def get_printable_deliverable_table(proposal_acronym):
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
    return DeliverableTablePrintable(items)


def get_printable_wp_deliverable_table(wp_object):
    proposal = wp_object.ref_proposal
    items = []
    for deliverable in wp_object.deliverables:
        items.append(dict(proposal_acronym=proposal.acronym, wp_number=wp_object.number,
                          responsible=deliverable.responsible, title=deliverable.title,
                          description=deliverable.description, due_month=deliverable.due_month,
                          type=deliverable.type, number=deliverable.number,
                          del_number=f'D{wp_object.number}.{deliverable.number}',
                          dissemination_level=deliverable.dissemination_level))
    return DeliverableTablePrintable(items)
