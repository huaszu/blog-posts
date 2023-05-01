from db.shared import db
from db.models.user import User
from db.models.post import Post
from db.utils import rows_to_list
from constants import MESSAGE_TYPE_AND_STATUS_CODE


PARAMETERS_ACCEPTED_VALUES = {"sortBy": ["id", "reads", "likes", "popularity"],
                              "direction": ["asc", "desc"]}


def check_user_exists(user_id):
    """Check by user id whether or not a user exists."""

    return User.query.get(user_id) is not None


def parse_author_ids(author_ids):
    try:
        parsed_author_ids: set[int] = set(int(author_id) for author_id in author_ids.split(",") if check_user_exists(int(author_id)))
        if not parsed_author_ids: 
            error_or_warning = "warning"
            return {"success": False, 
                    "message": {error_or_warning: "None of the author id(s) you requested exist in the database."}, 
                    "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}
        return {"success": True,
                "parsed_author_ids": parsed_author_ids}
    except:
        error_or_warning = "error"
        return {"success": False, 
                "message": {error_or_warning: "Please provide a query parameter value for `authorIds` as a number or as numbers separated by commas, such as '1,5'."}, 
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}


def validate_parameters_to_fetch_posts(parameters):
    # Check for 400 errors
    for parameter, value in parameters.items():
        if parameter in PARAMETERS_ACCEPTED_VALUES:
            acceptable = PARAMETERS_ACCEPTED_VALUES[parameter]
            if value not in acceptable:
                error_or_warning = "error"
                return {"success": False, 
                        "message": {error_or_warning: f"Unacceptable value for {parameter} query parameter.  We only accept one of {acceptable}."}, 
                        "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}
    author_ids: str = parameters.get("authorIds", None)
    if author_ids is None:
        error_or_warning = "error"
        return {"success": False, 
                "message": {error_or_warning: "Please identify author(s) using the query parameter key `authorIds`."}, 
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}
    
    # Either 400 with error message, 200 with warning message, or no problem
    else:
        return parse_author_ids(author_ids)


def display_posts(parsed_author_ids, sort_by, direction):
    posts_of_authors: list[Post] = Post.get_sorted_posts_by_user_ids(user_ids = parsed_author_ids,
                                                              sort_by=sort_by,
                                                              direction=direction)

    result = []

    listed_posts_of_authors: list[dict] = rows_to_list(posts_of_authors)

    post_properties = [property.name for property in Post.__table__.columns]
    post_properties.sort() # Example in specification indicates that response 
    # shows post properties in alphabetical order
    
    for post in listed_posts_of_authors:
        post_response = {post_property: post[post_property] for post_property in post_properties}
        result.append(post_response)

    return result    