from flask import Blueprint, request, jsonify
from services.auth import authenticate_user
from models.user import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and user.check_password(data['password']):
        token = authenticate_user(user.username)
        return jsonify({'token': token})
    return jsonify({'error': 'Invalid credentials'}), 401