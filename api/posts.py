from flask import jsonify, request, g, abort

from api import api
from db.shared import db
from db.models.user_post import UserPost
from db.models.post import Post, User

from db.utils import row_to_dict, rows_to_list
from middlewares import auth_required

from operator import itemgetter

import util.crud


POSTS_SORT_BY_OPTIONS: list[str] = ["id", "reads", "likes", "popularity"]
POSTS_SORT_DIRECTION_OPTIONS: list[str] = ["asc", "desc"]


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

    author_ids: str = request.args.get("authorIds", None)

    if author_ids is None:
        return jsonify({"error": "Please identify the author(s) whose posts to fetch using the query parameter key `authorIds`."}), 400

    sort_by: str = request.args.get("sortBy", "id")
    if sort_by not in POSTS_SORT_BY_OPTIONS:
        return jsonify({"error": "Unacceptable value for `sortBy` parameter.  We can sort by id, reads, likes, or popularity."}), 400

    direction: str = request.args.get("direction", "asc")
    if direction not in POSTS_SORT_DIRECTION_OPTIONS:
        return jsonify({"error": "Unacceptable value for `direction` parameter.  We only accept asc or desc."}), 400

    try:
        parsed_author_ids: set[int] = set(int(author_id) for author_id in author_ids.split(",") if util.crud.check_user_exists(int(author_id)))
    except:
        return jsonify({"error": "Please provide a query parameter value for `authorIds` as a number or as numbers separated by commas, such as '1,5'."}), 400

    if not parsed_author_ids: # Also helps to avoid the problem that subsequently 
        # running `Post.query.with_parent(user).all()` on users that do not 
        # exist will give an error
        return jsonify({"warning": "None of the author id(s) you requested exist in the database."}), 200

    # Fetch posts 

    posts_of_authors: set[Post] = set()

    for parsed_author_id in parsed_author_ids:
        try:
            posts_of_author: set[Post] = set(post for post in Post.get_posts_by_user_id(parsed_author_id))
            posts_of_authors.update(posts_of_author)
        except: # since None is not iterable, there could be an error if there are no posts for that parsed_author_id
            continue    
    # If after this for loop, posts_of_authors is still an empty set, then there are no posts to return

    if not posts_of_authors: 
        return jsonify({"posts": []}), 200

    listed_posts_of_authors: list[dict] = rows_to_list(posts_of_authors)
    sorted_posts: list[dict] = sorted(listed_posts_of_authors, key=itemgetter(sort_by), reverse=direction=="desc")

    # Alternative: Have SQLAlchemy help sort posts when querying database on line 89.
    # Not sure how much this alternative helps because we query database by
    # author id and ultimately we want to sort not on author id, but on
    # post id, reads, likes, or popularity.  There could be some benefit of, 
    # for each author, sorting by the desired one of the four sort by options
    # at the point of querying the database, and then preparing the final sort
    # later.  That could be investigated.

    result = []

    post_properties = list(sorted_posts[0].keys()) 
    post_properties.sort() # Example in specification indicates that response 
    # shows post properties in alphabetical order
    
    for post in sorted_posts:
        post_response = {post_property: post[post_property] for post_property in post_properties}
        result.append(post_response)

    return jsonify({"posts": result}), 200


@api.route("/posts/<postId>", methods=["PATCH"])
@auth_required
def update_post(postId):
    """
    Update blog post, if it exists in the database.  Return updated blog post.
    """
    # validation
    try:
        post = Post.get_post_by_post_id(int(postId))
        if post is None:
            return jsonify({"warning": "The post you requested does not exist in the database."}), 200
    except:
        return jsonify({"error": "Please use a number to represent the id of the post you want to update.  A sample acceptable path: /api/posts/1 versus a sample unacceptable path: /api/posts/one"}), 400

    user = g.get("user")
    if user.id not in [author.id for author in post.users]:
        return jsonify({"error": "Only an author of a post can update that post."}), 401

    # Update post

    print(post.users)
    print(post.tags)
    print(post.text)

    data = request.get_json(force=True)
    if "authorIds" in data:
        author_ids = data["authorIds"]

        if type(author_ids) is not list:
            return jsonify({"error": "Please use square brackets around the ids of the author(s) who should be the author(s) of the post you wish to update.  A sample acceptable input for authorIds: [1, 5] versus a sample unacceptable input for authorIds: 1,5"}), 400

        deduplicated_author_ids = set(author_ids)

        for author_id in deduplicated_author_ids:
            if type(author_id) is not int:
                return jsonify({"error": "Please check that each of your authorIds is a number."}), 400

        if len(author_ids) != len(User.query.filter(User.id.in_(author_ids)).all()):
            return jsonify({"error": "One or more authorIds provided is invalid.  Please check that each of your authorIds is an id of a user in the database."}), 400
        
        UserPost.query.filter_by(post_id=postId).delete()
        for author_id in deduplicated_author_ids:
            user_post = UserPost(user_id=author_id, post_id=postId)
            db.session.add(user_post)
    if "tags" in data:
        tags = data["tags"]
        if type(tags) is not list:
            return jsonify({"error": "Please use square brackets around the tag(s) that you want on the post.  Format your input for tags as an array of strings."}), 400

        for tag in tags:
            if type(tag) is not str:
                return jsonify({"error": "Please check that each tag is a string."}), 400
            
        post.tags = list(set(tags))
    if "text" in data:
        text = data["text"]
        if type(text) is not str:
            return jsonify({"error": "Please input the post text as a string."}), 400
        post.text = text
    db.session.commit()

    post = Post.get_post_by_post_id(postId)
    print(post.users)
    print(post.tags)
    print(post.text)

    post_response: dict = {"id": post.id, 
                           "authorIds": [user.id for user in post.users],
                           "likes": post.likes, 
                           "popularity": post.popularity,
                           "reads": post.reads,
                           "tags": post.tags,
                           "text": post.text} 

    return jsonify({"post": post_response}), 200