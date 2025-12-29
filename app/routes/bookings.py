from flask import Blueprint, jsonify

bp = Blueprint('bookings', __name__, url_prefix='/api/bookings')

@bp.route('/', methods=['GET'])
def get_bookings():
    return jsonify({'message': 'Get bookings endpoint placeholder'}), 200

@bp.route('/', methods=['POST'])
def create_booking():
    return jsonify({'message': 'Create booking endpoint placeholder'}), 201
