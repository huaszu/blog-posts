from db.shared import db
from db.models.post import Post

from api.util.constants import MESSAGE_TYPE_AND_STATUS_CODE
from repository_layer import database_operations


def validate_post_id(post_id: str):
    """Check that post id from URL path is valid."""
    try:
        post = Post.get_post_by_post_id(post_id=int(post_id))
        if post is None:
            error_or_warning: str = "warning"
            return {"success": False, 
                    "message": {error_or_warning: "The post you requested does not exist in the database."}, 
                    "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}
        else:
            return post
    except:
        error_or_warning: str = "error"
        return {"success": False, 
                "message": {error_or_warning: "Please use a number to represent the id of the post you want to update.  A sample acceptable path: /api/posts/1 versus a sample unacceptable path: /api/posts/one"},
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}


def validate_user_for_post_update(user, post):
    """Check whether user is an author of the post."""
    if user.id not in [author.id for author in post.users]:
        error_or_warning: str = "unauthorized"
        return {"success": False, 
                "message": {error_or_warning: "Only an author of a post can update that post."},
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}


def validate_data_present(raw_data):
    """Validate whether request has information about what modifications to make."""
    if raw_data is None:
        error_or_warning: str = "error"
        return {"success": False, 
                "message": {"error": "Please use --data-raw option to pass a JSON payload in the body of your request to indicate modifications."},
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}


def validate_authorIds_format(parsed_json) -> set[int]:
    """Validate that authorIds in request are provided correctly."""
    author_ids: list = parsed_json["authorIds"]

    if type(author_ids) is not list:
        error_or_warning: str = "error"
        return {"success": False, 
                "message": {error_or_warning: "Please use square brackets around the ids of the author(s) you want to see as the resulting author(s) of the post.  A sample acceptable input for authorIds: [1, 5] versus a sample unacceptable input for authorIds: 1,5"},
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}

    deduplicated_author_ids: set = set(author_ids)

    for author_id in deduplicated_author_ids:
        if type(author_id) is not int:
            error_or_warning: str = "error"
            return {"success": False, 
                "message": {error_or_warning: "Please check that each of your authorIds is a number."},
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}
                
    return deduplicated_author_ids
        

def validate_tags_format(parsed_json) -> list[str]:
    """Validate that tags in request are provided correctly."""
    tags: list = parsed_json["tags"]
    if type(tags) is not list:
        error_or_warning: str = "error"
        return {"success": False, 
                "message": {error_or_warning: "Please use square brackets around the tag(s) that you want on the post.  Format your input for tags as an array of strings."},
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}
        
    for tag in tags:
        if type(tag) is not str:
            error_or_warning: str = "error"
            return {"success": False, 
                "message": {error_or_warning: "Please check that each tag is a string."},
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}
        
    return tags
        

def validate_text_format(parsed_json) -> str:
    """Validate that text in request is provided correctly."""
    text: str = parsed_json["text"]
    if type(text) is not str:
        error_or_warning = "error"
        return {"success": False, 
                "message": {error_or_warning: "Please input the post text as a string."},
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]} 
    
    return text


def update_post(post, parsed_json):
    """Make updates to post.  Return updated post."""
    if "authorIds" in parsed_json:
        deduplicated_author_ids: set = validate_authorIds_format(parsed_json=parsed_json)
        database_operations.update_author_ids_of_post(post=post, 
                                                      deduplicated_author_ids=deduplicated_author_ids)

    if "tags" in parsed_json:
        tags: list = validate_tags_format(parsed_json=parsed_json)
        database_operations.update_tags_of_post(post=post, tags=tags)

    if "text" in parsed_json: 
        text: str = validate_text_format(parsed_json=parsed_json)
        database_operations.update_text_of_post(post=post, text=text)
    
    # Commit transaction after this batch of changes to get better
    # performance, maintain data integrity, and prevent inconsistent
    # states in the database.
    database_operations.commit_changes()

    return Post.get_post_by_post_id(post_id=int(post.id))
        

def generate_updated_post_response(existing_post, parsed_json) -> dict:
    """Return information about updated post in desired format."""
    updated_post = update_post(post=existing_post, parsed_json=parsed_json)
    updated_post_response: dict = {"id": updated_post.id, 
                                   "authorIds": [user.id for user in updated_post.users],
                                   "likes": updated_post.likes, 
                                   "popularity": updated_post.popularity,
                                   "reads": updated_post.reads,
                                   "tags": updated_post.tags,
                                   "text": updated_post.text} 
    return updated_post_response  