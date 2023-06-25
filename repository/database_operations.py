from db.shared import db
from db.models.user import User
from db.models.post import Post
from db.models.user_post import UserPost
from db.utils import rows_to_list


def get_user_by_id(user_id):
    """Get user by user id."""

    return User.query.get(user_id)


def filter_users_by_id(user_ids):
    """Filter users by user id."""

    return User.query.filter(User.id.in_(user_ids)).all()


def filter_user_posts_by_post_id(post_id):
    """Filter user posts by post id."""

    return UserPost.query.filter_by(post_id)


def create_user_post(user_id, post_id):
    """Create an instance of a UserPost object."""

    user_post = UserPost(user_id=user_id, post_id=post_id)

    return user_post