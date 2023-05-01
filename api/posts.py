from flask import jsonify, request, g, abort

from api import api
from db.shared import db
from db.models.user_post import UserPost
from db.models.post import Post, User

from db.utils import row_to_dict, rows_to_list
from middlewares import auth_required

from api.util import helpers_to_fetch_posts, helpers_to_update_post


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
    # validation
    user = g.get("user")
    if user is None:
        return abort(401)

    parameters = request.args

    # Handle errors in query parameter inputs from user
    result_of_parameter_checks = helpers_to_fetch_posts.validate_parameters_to_fetch_posts(parameters)
    if "error" in result_of_parameter_checks:
        return jsonify(result_of_parameter_checks), 400
    elif "warning" in result_of_parameter_checks:
        return jsonify(result_of_parameter_checks), 200
    else:
        parsed_author_ids = result_of_parameter_checks["parsed_author_ids"]
        
    sort_by: str = parameters.get("sortBy", "id")

    direction: str = parameters.get("direction", "asc")

    # Fetch posts 
    result = helpers_to_fetch_posts.display_posts(parsed_author_ids=parsed_author_ids, 
                                   sort_by=sort_by, 
                                   direction=direction)

    return jsonify({"posts": result}), 200


@api.route("/posts/<postId>", methods=["PATCH"])
@auth_required
def update_post(postId):
    """
    Update blog post, if it exists in the database.  Return updated blog post.
    """
    # validation
    result_of_post_id_check = helpers_to_update_post.validate_post_id(post_id=postId)
    if "error" in result_of_post_id_check:
        return jsonify(result_of_post_id_check), 400
    elif "warning" in result_of_post_id_check:
        return jsonify(result_of_post_id_check), 200
    else:
        post = result_of_post_id_check["post"]

    user = g.get("user")
    
    if "error" in helpers_to_update_post.validate_user_for_post_update(user, post):
        return jsonify(helpers_to_update_post.validate_user_for_post_update(user, post)), 401

    # Update post

    print(post.users)
    print(post.tags)
    print(post.text)

    parsed_json = request.get_json(force=True)
    if "authorIds" in parsed_json:
        result_of_update_authors = helpers_to_update_post.update_author_ids_of_post(post=post, parsed_json=parsed_json)
        if "error" in result_of_update_authors:
            return jsonify(result_of_update_authors), 400
  
    if "tags" in parsed_json:
        result_of_update_tags = helpers_to_update_post.update_tags_of_post(post=post, parsed_json=parsed_json)
        if "error" in result_of_update_tags:
            return jsonify(result_of_update_tags), 400

    if "text" in parsed_json:
        result_of_update_text = helpers_to_update_post.update_text_of_post(post=post, parsed_json=parsed_json)
        if "error" in result_of_update_text:
            return jsonify(result_of_update_text), 400

    db.session.commit()

    return jsonify({"post": helpers_to_update_post.format_post_for_response(post_id=postId)}), 200