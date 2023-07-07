from db.shared import db
from db.models.user import User
from db.models.user_post import UserPost

from api.util.constants import MESSAGE_TYPE_AND_STATUS_CODE


def get_user_by_id(user_id: int):
    """Get user by user id."""
    return User.query.get(user_id)


def filter_users_by_id(user_ids: set):
    """Filter users by user id."""
    return User.query.filter(User.id.in_(user_ids)).all()


def delete_user_post_by_post_id(post_id: int):
    """Delete user post by post id."""
    UserPost.query.filter_by(post_id=post_id).delete()
    db.session.commit()


def create_user_post(user_id: int, post_id: int):
    """Create an instance of a UserPost object."""
    user_post = UserPost(user_id=user_id, post_id=post_id)
    return user_post


def update_author_ids_of_post(post, deduplicated_author_ids) -> dict:
    """Update authors of post.  Handle applicable errors."""
    if len(deduplicated_author_ids) != len(filter_users_by_id(user_ids=deduplicated_author_ids)):
        error_or_warning: str = "error"
        return {"success": False, 
                "message": {error_or_warning: "One or more authorIds provided is invalid.  Please check that each of your authorIds is an id of a user in the database."},
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}

    delete_user_post_by_post_id(post_id=post.id)
    for author_id in deduplicated_author_ids:
        user_post = create_user_post(user_id=author_id, post_id=post.id)
        db.session.add(user_post)


def update_tags_of_post(post, tags) -> dict:
    """Update tags of post."""
    post.tags: list = tags 


def update_text_of_post(post, text) -> dict:
    """Update text of post."""
    post.text: str = text   


def commit_changes():
    """Commit transaction."""        
    db.session.commit()