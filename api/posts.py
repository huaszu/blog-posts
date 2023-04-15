from flask import jsonify, request, g, abort

from api import api
from db.shared import db
from db.models.user_post import UserPost
from db.models.post import Post

from db.utils import row_to_dict
from middlewares import auth_required


POSTS_SORT_BY_OPTIONS = ["id", "reads", "likes", "popularity"]


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

    if author_ids_string is None:
        return jsonify({"error": "Please identify the author(s) whose posts to fetch using the query parameter key `authorIds`"}), 400

    sort_by = request.args.get("sortBy", "id")
    if sort_by not in POSTS_SORT_BY_OPTIONS:
        return jsonify({"error": "Unacceptable value for `sortBy` parameter.  We can sort by id, reads, likes, or popularity."}), 400

    direction = request.args.get("direction", "asc")

    if direction == "asc":
        reverse_boolean = False
    elif direction == "desc": 
        reverse_boolean = True
    else:
        return jsonify({"error": "Unacceptable value for `direction` parameter.  We only accept asc or desc."}), 400

    author_ids_list = []

    try:
        for author_id in author_ids_string.split(","):
            if author_id not in author_ids_list:
                author_ids_list.append(int(author_id))
    except:
        return jsonify({"error": "Please provide a query parameter value for `authorIds` as a number or as numbers separated by commas, such as '1,2'."}), 400

    posts_of_authors = [] # list of Post objects

    for author in author_ids_list:
        # Later could combine with code on lines 86 through 94 by nesting
        # for loop to go through each of this author's posts and generate
        # posts_data dictionary without making posts_of_authors list
        posts_of_authors.extend(Post.get_posts_by_user_id(author))

    posts_data = {} # Dictionary helps ensure that each post shows up once in 
    # the data structure because each key of `post.id` is unique
    for post in posts_of_authors:
        posts_data[post.id] = {"id": post.id, # This key-value pair is redundant with the outer dictionary key.  What problems are we causing?
                               "likes": post.likes, 
                               "popularity": post.popularity,
                               "reads": post.reads,
                               "tags": post._tags.split(","),
                               "text": post.text}

    def sort_posts_on(item):
        return item[1][sort_by]

    sorted_posts = sorted(posts_data.items(), key=sort_posts_on, reverse=reverse_boolean) # a list of tuples
    # Alternative: Have SQLAlchemy help sort posts when querying database on line 60
    
    result_list = []
    for post_tuple in sorted_posts:
        result_list.append(post_tuple[1])

    return jsonify({"posts": result_list}), 200