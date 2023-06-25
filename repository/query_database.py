from db.shared import db
from db.models.user import User
from db.models.post import Post
from db.utils import rows_to_list


def get_user_by_id(user_id):
    """Get user by user id."""

    return User.query.get(user_id)