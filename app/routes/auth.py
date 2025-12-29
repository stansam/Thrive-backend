from flask import Blueprint, jsonify

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@bp.route('/register', methods=['POST'])
def register():
    return jsonify({'message': 'Register endpoint placeholder'}), 201

@bp.route('/login', methods=['POST'])
def login():
    return jsonify({'message': 'Login endpoint placeholder'}), 200
