from flask import jsonify, request, g, abort

from api import api
from db.shared import db
from db.models.user_post import UserPost
from db.models.post import Post

from db.utils import row_to_dict
from api.util import helpers_to_fetch_posts, helpers_to_update_post
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
    # Validation
    user = g.get("user")
    if user is None:
        return abort(401)

    parameters = request.args
    parsed_author_ids: set[int] = helpers_to_fetch_posts.create_author_ids_response(parameters=parameters)        
    sort_by: str = parameters.get("sortBy", "id")
    direction: str = parameters.get("direction", "asc")

    # Fetch posts 
    result = helpers_to_fetch_posts.display_posts(parsed_author_ids=parsed_author_ids, 
                                                  sort_by=sort_by, 
                                                  direction=direction)
    return jsonify({"posts": result}), 200


@api.route("/posts/<postId>", methods=["PATCH"])
@auth_required
def update_post(postId: str):
    """
    Update blog post, if it exists in the database.  Return updated blog post.
    """
    existing_post = helpers_to_update_post.validate_post_id(post_id=postId)

    # Validation
    user = g.get("user")    
    helpers_to_update_post.validate_user_for_post_update(user=user, 
                                                         post=existing_post)

    # Check that request contains information about updates to make
    helpers_to_update_post.validate_data_present(raw_data=request.data)

    parsed_json = request.get_json(force=True)
    
    # Update post and return specified response
    result = helpers_to_update_post.generate_updated_post_response(existing_post=existing_post, 
                                                                   parsed_json=parsed_json)
    return jsonify({"post": result}), 200