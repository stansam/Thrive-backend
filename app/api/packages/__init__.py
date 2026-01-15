from flask import Blueprint

packages_bp = Blueprint('packages', __name__, url_prefix='/api/packages')

from . import search, listings, details, favorites