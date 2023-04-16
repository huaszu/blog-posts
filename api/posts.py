from flask import jsonify, request, g, abort

from api import api
from db.shared import db
from db.models.user_post import UserPost
from db.models.post import Post

from db.utils import row_to_dict
from middlewares import auth_required

import crud


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
    author_ids_input: str = request.args.get("authorIds", None)

    if author_ids_input is None:
        return jsonify({"error": "Please identify the author(s) whose posts to fetch using the query parameter key `authorIds`."}), 400

    sort_by_input: str = request.args.get("sortBy", "id")
    if sort_by_input not in POSTS_SORT_BY_OPTIONS:
        return jsonify({"error": "Unacceptable value for `sortBy` parameter.  We can sort by id, reads, likes, or popularity."}), 400

    direction_input: str = request.args.get("direction", "asc")
    if direction_input not in POSTS_SORT_DIRECTION_OPTIONS:
        return jsonify({"error": "Unacceptable value for `direction` parameter.  We only accept asc or desc."}), 400

    author_ids: set[int] = set()

    try:
        for author_id_input in author_ids_input.split(","):
            author_id = int(author_id_input)
            if crud.check_user_exists(author_id):
                author_ids.add(author_id)
    except:
        return jsonify({"error": "Please provide a query parameter value for `authorIds` as a number or as numbers separated by commas, such as '1,5'."}), 400

    if not author_ids: # Also helps to avoid the problem that subsequently 
        # running `Post.query.with_parent(user).all()` on users that do not 
        # exist will give an error
        return jsonify({"error": "None of the author id(s) you requested exist in the database."}), 200

    posts_of_authors: set[Post] = set()

    for author_id in author_ids:
        for post in Post.get_posts_by_user_id(author_id):
            posts_of_authors.add(post)
   
    if not posts_of_authors: # If posts_of_authors is empty, the later code to
        # populate the `posts_data` dictionary will give an error so let's 
        # avoid that
        return jsonify({"posts": []}), 200

    posts_data: dict[int, dict] = {} 

    for post in posts_of_authors:
        posts_data[post.id] = {"id": post.id, # This key-value pair is redundant with the outer dictionary key.  What problems are we causing?
                                "likes": post.likes, 
                                "popularity": post.popularity,
                                "reads": post.reads,
                                "tags": post._tags.split(","),
                                "text": post.text}        
        # Alternative: For each post, make a dictionary in the format of the 
        # inner dictionary above.  Have a list of these dictionaries.  Later 
        # can sort the list as desired.  However, generating this outer 
        # dictionary of dictionaries seems more extensible and has better time
        # complexity if we want to look up a post (though arguably we could 
        # just access the db to get a post's info - depends on the context, 
        # what the API user might want to do in the future, what access the 
        # user has, whom and what we are building for, et al)                            

    def sort_posts_on(item):
        return item[1][sort_by_input]

    if direction_input == "asc":
        reverse_boolean: bool = False
    else: 
        reverse_boolean: bool = True

    sorted_posts: list[tuple] = sorted(posts_data.items(), key=sort_posts_on, reverse=reverse_boolean)
    # Alternative: Have SQLAlchemy help sort posts when querying database on line 85.
    # Not sure how much this alternative helps because we query database by
    # author id and ultimately we want to sort not on author id, but on
    # post id, reads, likes, or popularity.  There could be some benefit of, 
    # for each author, sorting by the desired one of the four sort by options
    # at the point of querying the database, and then preparing the final sort
    # later.  That could be investigated.
    
    result: list[dict] = []
    for post_response in sorted_posts:
        result.append(post_response[1])

    return jsonify({"posts": result}), 200