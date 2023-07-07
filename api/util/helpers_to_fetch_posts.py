from db.shared import db
from db.models.post import Post

from db.utils import rows_to_list
from api.util.constants import MESSAGE_TYPE_AND_STATUS_CODE, PARAMETERS_ACCEPTED_VALUES
from repository_layer import database_operations


def check_user_exists(user_id: int) -> bool:
    """Check by user id whether or not a user exists."""
    return database_operations.get_user_by_id(user_id=user_id) is not None


def parse_author_ids(author_ids: str):
    """Parse author ids.  If not possible, give user error messaging."""
    try:
        parsed_author_ids: set = set(int(author_id) for author_id in author_ids.split(",") if check_user_exists(int(author_id)))
        if not parsed_author_ids: 
            error_or_warning: str = "warning"
            return {"success": False, 
                    "message": {error_or_warning: "None of the author id(s) you requested exist in the database."}, 
                    "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}
        return parsed_author_ids
    except:
        error_or_warning: str = "error"
        return {"success": False, 
                "message": {error_or_warning: "Please provide a query parameter value for `authorIds` as a number or as numbers separated by commas, such as '1,5'."}, 
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}


def validate_parameters_accepted_values(parameters: dict):
    """Validate that parameters have acceptable values."""
    for parameter, value in parameters.items():
        if parameter in PARAMETERS_ACCEPTED_VALUES:
            acceptable: list[str] = PARAMETERS_ACCEPTED_VALUES[parameter]
            if value not in acceptable:
                error_or_warning: str = "error"
                return {"success": False, 
                        "message": {error_or_warning: f"Unacceptable value for {parameter} query parameter.  We only accept one of {acceptable}."}, 
                        "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}
        # Note: If user includes query parameter keys not among the
        # expected ones, i.e., not "sortBy" or "direction", process 
        # request ignoring irrelevant parameter keys.    


def validate_authorIds_exist_in_request(parameters: dict):
    """Validate that request provided authorIds."""
    author_ids: str = parameters.get("authorIds", None)
    if author_ids is None:
        error_or_warning: str = "error"
        return {"success": False, 
                "message": {error_or_warning: "Please identify author(s) using the query parameter key `authorIds`."}, 
                "status_code": MESSAGE_TYPE_AND_STATUS_CODE[error_or_warning]}
    return author_ids    


def create_author_ids_response(parameters: dict):
    """If parameters valid, return information containing parsed ids.  If not, give error messaging."""
    validate_parameters_accepted_values(parameters=parameters)
    author_ids: str = validate_authorIds_exist_in_request(parameters=parameters)           
    return parse_author_ids(author_ids=author_ids)


def display_posts(parsed_author_ids, sort_by, direction) -> list[dict]:
    """Create response to user showing posts with applicable sorting."""
    posts_of_authors: list[Post] = Post.get_sorted_posts_by_user_ids(user_ids=parsed_author_ids,
                                                                     sort_by=sort_by,
                                                                     direction=direction)

    result: list = []

    listed_posts_of_authors: list[dict] = rows_to_list(posts_of_authors)

    post_properties: list = [property.name for property in Post.__table__.columns]
    post_properties.sort() # Example in specification indicates that 
    # response shows post properties in alphabetical order
    
    for post in listed_posts_of_authors:
        post_response: dict = {post_property: post[post_property] for post_property in post_properties}
        result.append(post_response)

    return result