from db.shared import db
from db.models.user import User

def check_user_exists(user_id):
    """Check by user id whether or not a user exists."""

    return User.query.get(user_id) is not None