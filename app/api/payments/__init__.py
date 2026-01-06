from flask import Blueprint
from flask_cors import CORS

payment_bp = Blueprint('payments', __name__, url_prefix='/api/payments')
CORS(payment_bp)

from app.api.payments import routes