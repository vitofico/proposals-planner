from flask import jsonify, request, url_for, g, abort
from app import db
from app.models import User, Proposal
from app.api import bp
from app.api.auth import token_auth
from app.api.errors import bad_request


@bp.route('/proposals/<int:id>', methods=['GET'])
@token_auth.login_required
def get_proposal(id):
    proposal = Proposal.query.get(id)
    if proposal.user_is_included(g.current_user):
        return jsonify(Proposal.query.get_or_404(id).to_dict())
    else:
        return bad_request('user not allowed')


#
@bp.route('/proposals', methods=['GET'])
@token_auth.login_required
def get_proposals():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 100)
    data = Proposal.to_collection_dict(Proposal.query, page, per_page, 'api.get_proposals')
    return jsonify(data)


#
#
@bp.route('/proposals/<int:id>/wps', methods=['GET'])
@token_auth.login_required
def get_wps(id):
    proposal = Proposal.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 100)
    data = Proposal.to_collection_dict(proposal.working_packages, page, per_page,
                                       'api.get_wps', id=id)
    return jsonify(data)
#
#
# @bp.route('/users/<int:id>/followed', methods=['GET'])
# @token_auth.login_required
# def get_followed(id):
#     user = User.query.get_or_404(id)
#     page = request.args.get('page', 1, type=int)
#     per_page = min(request.args.get('per_page', 10, type=int), 100)
#     data = User.to_collection_dict(user.followed, page, per_page,
#                                    'api.get_followed', id=id)
#     return jsonify(data)
#
#
# @bp.route('/users', methods=['POST'])
# def create_user():
#     data = request.get_json() or {}
#     if 'username' not in data or 'email' not in data or 'password' not in data:
#         return bad_request('must include username, email and password fields')
#     if User.query.filter_by(username=data['username']).first():
#         return bad_request('please use a different username')
#     if User.query.filter_by(email=data['email']).first():
#         return bad_request('please use a different email address')
#     user = User()
#     user.from_dict(data, new_user=True)
#     db.session.add(user)
#     db.session.commit()
#     response = jsonify(user.to_dict())
#     response.status_code = 201
#     response.headers['Location'] = url_for('api.get_user', id=user.id)
#     return response
#
#
# @bp.route('/users/<int:id>', methods=['PUT'])
# @token_auth.login_required
# def update_user(id):
#     if g.current_user.id != id:
#         abort(403)
#     user = User.query.get_or_404(id)
#     data = request.get_json() or {}
#     if 'username' in data and data['username'] != user.username and \
#             User.query.filter_by(username=data['username']).first():
#         return bad_request('please use a different username')
#     if 'email' in data and data['email'] != user.email and \
#             User.query.filter_by(email=data['email']).first():
#         return bad_request('please use a different email address')
#     user.from_dict(data, new_user=False)
#     db.session.commit()
#     return jsonify(user.to_dict())