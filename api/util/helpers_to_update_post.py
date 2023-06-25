from db.shared import db
from db.models.user import User
from db.models.post import Post
from db.models.user_post import UserPost
from constants import MESSAGE_TYPE_AND_STATUS_CODE
from repository import database_operations


def validate_post_id(post_id):
    try:
        post = Post.get_post_by_post_id(int(post_id))
        if post is None:
            error_or_warning = "warning"
            return {"success": False, 
                    "message": {error_or_warning: "The post you requested does not exist in the database."}, 
                    "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}
        else:
            return {"success": True, "post": post}
    except:
        error_or_warning = "error"
        return {"success": False, 
                "message": {error_or_warning: "Please use a number to represent the id of the post you want to update.  A sample acceptable path: /api/posts/1 versus a sample unacceptable path: /api/posts/one"},
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}


def validate_user_for_post_update(user, post):
    if user.id not in [author.id for author in post.users]:
        error_or_warning = "error"
        return {"success": False, 
                "message": {error_or_warning: "Only an author of a post can update that post."},
                "status_code": 401}
    return {"success": True}


def validate_data_present(raw_data):
    if raw_data is None:
        error_or_warning = "error"
        return {"success": False, 
                "message": {"error": "Please use --data-raw option to pass a JSON payload in the body of your request to indicate modifications."},
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}
    return {"success": True}        


def update_author_ids_of_post(post, parsed_json):
    author_ids = parsed_json["authorIds"]

    if type(author_ids) is not list:
        error_or_warning = "error"
        return {"success": False, 
                "message": {error_or_warning: "Please use square brackets around the ids of the author(s) who should be the author(s) of the post you wish to update.  A sample acceptable input for authorIds: [1, 5] versus a sample unacceptable input for authorIds: 1,5"},
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}

    deduplicated_author_ids = set(author_ids)

    for author_id in deduplicated_author_ids:
        if type(author_id) is not int:
            error_or_warning = "error"
            return {"success": False, 
                "message": {error_or_warning: "Please check that each of your authorIds is a number."},
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}

    if len(author_ids) != len(database_operations.filter_users_by_id(user_ids=author_ids)):
        error_or_warning = "error"
        return {"success": False, 
                "message": {error_or_warning: "One or more authorIds provided is invalid.  Please check that each of your authorIds is an id of a user in the database."},
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}

    database_operations.filter_user_posts_by_post_id(post_id=post.id).delete()
    for author_id in deduplicated_author_ids:
        user_post = database_operations.create_user_post(user_id=author_id, post_id=post.id)
        db.session.add(user_post)
    return {"success": True}


def update_tags_of_post(post, parsed_json):
    tags = parsed_json["tags"]
    if type(tags) is not list:
        error_or_warning = "error"
        return {"success": False, 
                "message": {error_or_warning: "Please use square brackets around the tag(s) that you want on the post.  Format your input for tags as an array of strings."},
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}
        
    for tag in tags:
        if type(tag) is not str:
            error_or_warning = "error"
            return {"success": False, 
                "message": {error_or_warning: "Please check that each tag is a string."},
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}
            
    post.tags = tags   
    return {"success": True}


def update_text_of_post(post, parsed_json):
    text = parsed_json["text"]
    if type(text) is not str:
        error_or_warning = "error"
        return {"success": False, 
                "message": {error_or_warning: "Please input the post text as a string."},
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}

    post.text = text   
    return {"success": True}


def format_post_for_response(post_id):
    post = Post.get_post_by_post_id(post_id=post_id)
    post_response: dict = {"id": post.id, 
                           "authorIds": [user.id for user in post.users],
                           "likes": post.likes, 
                           "popularity": post.popularity,
                           "reads": post.reads,
                           "tags": post.tags,
                           "text": post.text} 
    print(post.users)
    print(post.tags)
    print(post.text)
    return post_response  