from db.shared import db
from db.models.user import User


PARAMETERS_ACCEPTED_VALUES = {"sortBy": ["id", "reads", "likes", "popularity"],
                              "direction": ["asc", "desc"]}


def check_user_exists(user_id):
    """Check by user id whether or not a user exists."""

    return User.query.get(user_id) is not None


def parse_author_ids(author_ids):
    try:
        parsed_author_ids: set[int] = set(int(author_id) for author_id in author_ids.split(",") if check_user_exists(int(author_id)))
        if not parsed_author_ids: 
            return {"warning": "None of the author id(s) you requested exist in the database."}
        return {"parsed_author_ids": parsed_author_ids}
    except:
        return {"error": "Please provide a query parameter value for `authorIds` as a number or as numbers separated by commas, such as '1,5'."}


def validate_parameters_to_fetch_posts(parameters):
    # 400 Errors
    for parameter, value in parameters.items():
        if parameter in PARAMETERS_ACCEPTED_VALUES:
            acceptable = PARAMETERS_ACCEPTED_VALUES[parameter]
            if value not in acceptable:
                return {"error": f"Unacceptable value for {parameter} query parameter.  We only accept one of {acceptable}."}
    author_ids: str = parameters.get("authorIds", None)
    if author_ids is None:
        return {"error": "Please identify the author(s) whose posts to fetch using the query parameter key `authorIds`."}
    
    # Either 400 with error message, 200 with warning message, or no problem
    else:
        return parse_author_ids(author_ids)




    # for query_parameter, values in parameters.items():
    #     if query_parameter == "authorIds":
    #         author_id_validation = validate_author_ids(values)
    #         if author_id_validation.get("status_code") == 400:
    #             return {"error": author_id_validation["message"]}
    #         elif author_id_validation.get("warning") is not None:
    #             return {"warning": author_id_validation["warning"]}
    #         else:
    #             parsed_author_ids = author_id_validation["parsed_author_ids"]
    #     if query_parameter == "sortBy":
    #         sort_by: str = values
    #         return validate_parameter_value(parameter=query_parameter, value=sort_by)
    #     if query_parameter == "direction":
    #         direction: str = values
    #         return validate_parameter_value(parameter=query_parameter, value=direction)


def validate_parameter_value(parameter, value):
    if value not in PARAMETERS_ACCEPTED_VALUES[parameter]:
        return {"success": False,
                "message": f"Unacceptable value for {parameter} query parameter.  We only accept one of {PARAMETERS_ACCEPTED_VALUES[parameter]}."}
    else:
        return {"success": True}

def validate_author_ids(author_ids: str) -> set[int]:
    if author_ids is None:
        return {"success": False, 
                "message": "Please identify the author(s) using the query parameter key `authorIds`.",
                "status_code": 400}

    try:
        parsed_author_ids: set[int] = set(int(author_id) for author_id in author_ids.split(",") if check_user_exists(int(author_id)))
        if not parsed_author_ids: 
            return {"success": False,
                    "warning": "None of the author id(s) you requested exist in the database.",
                    "status_code": 200}
        return {"success": True,
                "parsed_author_ids": parsed_author_ids}
    except:
        return {"success": False, 
                "message": "Please provide a query parameter value for `authorIds` as a number or as numbers separated by commas, such as '1,5'.",
                "status_code": 400}