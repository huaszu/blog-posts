from flask import jsonify, request, g, abort

from api import api
from db.shared import db
from db.models.user_post import UserPost
from db.models.post import Post

from db.utils import row_to_dict
from middlewares import auth_required


@api.post("/posts")
@auth_required
def posts():
    # validation
    user = g.get("user")
    if user is None:
        return abort(401)

    data = request.get_json(force=True)
    text = data.get("text", None)
    tags = data.get("tags", None)
    if text is None:
        return jsonify({"error": "Must provide text for the new post"}), 400

    # Create new post
    post_values = {"text": text}
    if tags:
        post_values["tags"] = tags

    post = Post(**post_values)
    db.session.add(post)
    db.session.commit()

    user_post = UserPost(user_id=user.id, post_id=post.id)
    db.session.add(user_post)
    db.session.commit()

    return row_to_dict(post), 200


@api.route("/posts", methods=["GET"])
@auth_required
def fetch_posts():
    """
    Fetch blog posts that have at least one of the authors specified.
    """
    author_ids_string = request.args.get("authorIds", None)
    sort_by = request.args.get("sortBy", "id")
    direction = request.args.get("direction", "asc")

    author_ids_list = []
    for author_id in author_ids_string.split(","):
        author_ids_list.append(int(author_id))

    # print(author_ids_list)

    posts_of_authors = [] # list of Post objects

    for author in author_ids_list:
        posts_of_authors.extend(Post.get_posts_by_user_id(author))

    return jsonify({"authorIds": author_ids_string, "sortBy": sort_by, "direction": direction}), 200
