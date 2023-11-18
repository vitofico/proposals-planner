from dateutil.relativedelta import relativedelta
from trello import TrelloClient


# client = TrelloClient(
#     api_key='6a24b5bd89beced4eddefcf1cda4da88',
#     api_secret='6a24b5bd89beced4eddefcf1cda4da88',
#     token='c203194655212e7d06641856665c85ff3d9bae3c5f2edc0253c9a74a3b8723da',
#     token_secret='c203194655212e7d06641856665c85ff3d9bae3c5f2edc0253c9a74a3b8723da'
# )

# client
# [ 'add_star', 'api_key', 'api_secret', 'create_hook', 'delete_star', 'fetch_json', 'get_board', 'get_card', 'get_label', 'get_list', 'get_member', 'get_organization', 'http_service', 'info_for_all_boards', 'list_boards', 'list_hooks', 'list_organizations', 'list_stars', 'logout', 'oauth', 'proxies', 'public_only', 'resource_owner_key', 'resource_owner_secret', 'search']
# board
# ['_date_last_activity', 'add_custom_field_definition', 'add_label', 'add_list', 'add_member', 'admin_members', 'all_cards', 'all_lists', 'all_members', 'client', 'close', 'closed', 'closed_cards', 'closed_lists', 'customFieldDefinitions', 'date_last_activity', 'delete_custom_field_definition', 'delete_label', 'description', 'fetch', 'fetch_actions', 'from_json', 'get_cards', 'get_checklists', 'get_custom_field_definitions', 'get_labels', 'get_last_activity', 'get_list', 'get_lists', 'get_members', 'id', 'list_lists', 'name', 'normal_members', 'open', 'open_cards', 'open_lists', 'owner_members', 'remove_member', 'save', 'set_description', 'set_name', 'set_organization', 'url', 'visible_cards']
# list
# ['add_card', 'archive_all_cards', 'board', 'cardsCnt', 'client', 'close', 'closed', 'fetch', 'fetch_actions', 'from_json', 'id', 'list_cards', 'list_cards_iter', 'move', 'move_all_cards', 'name', 'open', 'pos', 'set_name', 'set_pos', 'subscribe', 'subscribed', 'unsubscribe']
# card
# ['add_checklist', 'add_label', 'add_member', 'assign', 'attach', 'attachments', 'attriExp', 'badges', 'board', 'board_id', 'card_created_date', 'change_board', 'change_list', 'change_pos', 'checklists', 'client', 'closed', 'comment', 'comments', 'countCheckItems', 'create_label', 'created_date', 'customFields', 'custom_fields', 'dateLastActivity', 'date_last_activity', 'delete', 'delete_comment', 'desc', 'description', 'due', 'due_date', 'fetch', 'fetch_actions', 'fetch_attachments', 'fetch_checklists', 'fetch_comments', 'fetch_custom_fields', 'fetch_plugin_data', 'from_json', 'get_attachments', 'get_comments', 'get_custom_field_by_name', 'get_list', 'get_stats_by_list', 'id', 'idBoard', 'idLabels', 'idList', 'idMembers', 'idShort', 'is_due_complete', 'labels', 'latestCardMove_date', 'listCardMove_date', 'list_id', 'list_movements', 'member_id', 'member_ids', 'name', 'plugin_data', 'pos', 'remove_attachment', 'remove_due', 'remove_due_complete', 'remove_label', 'remove_member', 'set_closed', 'set_custom_field', 'set_description', 'set_due', 'set_due_complete', 'set_name', 'set_pos', 'shortUrl', 'short_id', 'short_url', 'subscribe', 'trello_list', 'unassign', 'update_comment', 'url']


def get_board_byname(client, board_name):
    ''' Case insensitive search. Returns last matched board object or creates a new one '''
    all_boards = client.list_boards()
    result = [x for x in all_boards if board_name.lower() in x.name.lower()]
    if result:
        return result[-1]
    else:
        return client.add_board(board_name)


def clean_board(board):
    [x.delete() for x in board.get_cards()]
    return board


def get_list_byname(board, list_name):
    ''' Case insensitive search. Returns last matched list object or creates a new one '''
    result = [x for x in board.all_lists() if list_name.lower() in x.name.lower()]
    if result:
        return result[-1]
    else:
        return board.add_list(list_name)


def clean_list(list):
    [x.delete() for x in list.list_cards()]
    return list


def get_card_byname(card_list, card_name):
    ''' Case insensitive search. Returns last matched card object or creates a new one '''
    result = [x for x in card_list.list_cards() if card_name.lower() in x.name.lower()]
    if result:
        return result[-1]
    else:
        return card_list.add_card(card_name)


def secure_set_description(card, description):
    try:
        card.set_description(description)
        return True
    except:
        return False


def wp_card_text(work_package):
    title = f'WP{work_package.number} - {work_package.title} [{work_package.get_leader_acronym()}]'
    effort_summary = '\n'.join([f'{item.company.acronym} = {item.person_month}PM' for item in
                                work_package.company_participant])
    description = f'{work_package.description}\n\n ## Effort Summary \n {effort_summary}'
    return title, description


def del_card_text(deliverable):
    title = f'D{deliverable.ref_wp.number}.{deliverable.number} - {deliverable.title} [{deliverable.responsible}]'
    description = f'{deliverable.description} \n\nType: {deliverable.type} \nDissemination Level: {deliverable.dissemination_level}'
    return title, description


def mil_card_text(milestone):
    title = f'M{milestone.number} - {milestone.title} [{milestone.responsible}]'
    description = f'{milestone.description}'
    return title, description


def execute_send_trello(app, proposal, user):
    with app.app_context():
        send_proposal_to_trello(proposal=proposal, user=user)


def send_proposal_to_trello(proposal, user):
    try:
        client = TrelloClient(api_key=user.trello_api_key, api_secret=user.trello_api_key, token=user.trello_token,
                              token_secret=user.trello_token)
        project_board = get_board_byname(client=client, board_name=proposal.acronym)
        # Project List
        list_name = 'Project'
        project_list = get_list_byname(board=project_board, list_name=list_name)
        abstract_card = get_card_byname(card_list=project_list, card_name='Abstract')
        secure_set_description(card=abstract_card, description=proposal.description)
        contacts_card = get_card_byname(card_list=project_list, card_name='Contacts List')
        description = '\n'.join(
            [f'{item.user.name} {item.user.surname.upper()} - {item.user.email}' for item in proposal.user_membership])
        secure_set_description(card=contacts_card, description=description)

        # WPs List
        list = get_list_byname(board=project_board, list_name='Work Packages')
        wps_list = clean_list(list=list)
        list = get_list_byname(board=project_board, list_name='Deliverables')
        del_list = clean_list(list=list)
        list = get_list_byname(board=project_board, list_name='Milestones')
        mil_list = clean_list(list=list)
        for work_package, label in zip(proposal.working_packages, project_board.get_labels()):
            title, description = wp_card_text(work_package)
            wpcard = get_card_byname(card_list=wps_list, card_name=title)
            secure_set_description(card=wpcard, description=description)
            wpcard.set_due(proposal.start_date + relativedelta(months=work_package.end_month))
            wpcard.add_label(label)
            for deliverable in work_package.deliverables:
                title, description = del_card_text(deliverable)
                del_card = get_card_byname(card_list=del_list, card_name=title)
                secure_set_description(card=del_card, description=description)
                del_card.set_due(proposal.start_date + relativedelta(months=deliverable.due_month))
                del_card.add_label(label)

            for milestone in work_package.milestones:
                title, description = mil_card_text(milestone)
                mil_card = get_card_byname(card_list=mil_list, card_name=title)
                secure_set_description(card=mil_card, description=description)
                mil_card.set_due(proposal.start_date + relativedelta(months=milestone.due_month))
                mil_card.add_label(label)
        return 'Proposal correctly submitted to your Trello account'
    except Exception as e:
        return e
