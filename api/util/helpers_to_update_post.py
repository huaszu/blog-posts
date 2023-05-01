from db.shared import db
from db.models.post import Post


def validate_post_id(post_id):
    try:
        post = Post.get_post_by_post_id(int(post_id))
        if post is None:
            return {"warning": "The post you requested does not exist in the database."}
        else:
            return {"post": post}
    except:
        return {"error": "Please use a number to represent the id of the post you want to update.  A sample acceptable path: /api/posts/1 versus a sample unacceptable path: /api/posts/one"}
