# Roles

## Table of Contents
- [Question 1](#question-1)
- [Question 2](#question-2)
- [Alternatives considered](#alternatives-considered)
- [Adjacent concerns](#adjacent-concerns)
- [Footnotes](#footnotes)

## Question 1 
### What database changes would be required to the starter code to allow for different roles for authors of a blog post? Imagine that we’d want to also be able to add custom roles and change the permission sets for certain roles on the fly without any code changes.

Given the scoping of this request from the product team, let's assume that we are concerned with managing what a user can do on a blog post when the user is an author of that post.  We assume that we are solving for places in the code where there is already or will be code that checks that a user is an author of a post - given that, we are now figuring out how to guide what a particular author can do.  

Many web frameworks have role-based access control (RBAC) libraries available that we should use because security is so important and difficult.  See [below](#flask-rbac-module) for information regarding Flask’s RBAC module.  For the purpose of this exercise, here is a hand-written solution: 

I propose changes to enable the database to keep track of what roles are possible, what each role's permission set is, and which roles each author has.  Here is an implementation: 

- Introduce `role_permissions`, `role_name`, `capability` tables that help us track what each role's permission set is.  To start, we have `owner`, `editor`, and `viewer` roles, per the question prompt.  In this example, a role can have one or more capabilities.  A capability is represented by the name of a function in the code that the role has permission to run[^1]. To meet the product requirement that **only owners of a blog post can modify the authors' list to a blog post (adding more authors, changing their role)**, we see that only `owner` has permission to `/repository_layer/database_operations.py/update_author_ids_of_post`: 

`role_name`
| role_id         | role_name       |
|-----------------|-----------------|
| 1               | owner           | 
| 2               | editor          |   
| 3               | viewer          |

`role_id`: primary key.  `role_name` cannot be null. 

Having a separate `role_name` table prevents repeating role names in the rows of the `role_permissions` table and enables clarity in the future as we evolve the roles, add roles, or want to change what a role is named. 

`capability`
| capability_id   | function_name                |
|-----------------|------------------------------|
| 1               | update_author_ids_of_post    | 
| 2               | update_tags_of_post          |   
| 3               | update_text_of_post          |

`capability_id`: primary key.  `function_name` cannot be null. 

`role_permissions` [^2]
| role_id         | capability_id  |
|-----------------|----------------|
| 1               | 1              | 
| 1               | 2              |   
| 1               | 3              |
| 2               | 1              |   
| 2               | 2              | 

`role_id`: foreign key that references `role_id` from `role_name` table. 
`capability_id`: foreign key that references `capability_id` from `capability` table. 

  - Since we care about ability to **add custom roles and change the permission sets for certain roles on the fly**, I decided to go with a separate `role_permissions` table that represents each role's permission set, and assigning each user a role in relation to each post, as opposed to more manually setting each user's permissions.  We modify roles in the `role_permissions` table.

- Add a column to the `user_post` table that indicates the role of each user for each associated post.  This design is because we want to allow the same user to have different roles depending on which post is at hand.  A user can be only a viewer of one blog post while being an owner of a different blog post.  Here is how this suggested change to the `user_post` table could look:

`user_post` [^3]
| user_id      | post_id       | role_id |
|--------------|---------------|---------|
| 1            | 1             | 1       |
| 2            | 1             | 1       |
| 2            | 2             | 2       |
| 2            | 3             | 2       |
| 3            | 3             | 2       |
| 3            | 4             | 3       | 

  - Enforce that every record in the `user_post` table have a non-null value for `role_id`.  For example, at the point of `user_post` record creation, we could set a default that the `role_id` is `3`, corresponding to `viewer` and offer ability to indicate a different role.  Depending on the role of the user who is wanting to indicate a different role, there may be limits on what roles we allow that user to give out.  We can speak with business and user experience stakeholders about the business logic - for example, if a user originated a post, perhaps this user should automatically be given an `owner` role, with `role_id` `1` for that post, which is one way to support the product requirement that **for any blog post, there must always be at least one owner of the blog post.**  In this solution, the program that adds a new post record to the `post` table and makes the pertinent updates to the `user_post` table could make that `role_id == 1` assignment to that user. There may be nuances, such as additional logic that initially makes this user's role `editor` and upgrades the role to `owner`, depending on whether or not the user has also verified their email or identity or taken other actions germane to the business context. 

  - Let's require in the `user_post` table that the value for `role_id` be from among the roles in the `role_name` table.  If at the point of `role_id` assignment for a `user_post` record, a user wants to create an entirely new role, we can plan for the circumstances when that should or should not be enabled in our business context and put in place a process or tooling that considers security and the user experience. 

- Because **for any blog post, there must always be at least one owner of the blog post**, incorporate **model validation** so that every time the model is saved, check that each post has at least one author having an `owner` role.  Using SQLAlchemy's event system: Use `before_insert`, `before_update`, and `before_flush` event listeners to perform checks and when the validation fails, raise an exception with a useful message, such as "At least one author must have the role "owner" for every post."

- Encapsulate RBAC checks in a method in the `User` class so that callers can use `User.can_update_author_ids_of_post(post_id)` rather than having to know about the table structure: 
A `User.can_update_author_ids_of_post(post_id)` method uses the `user_id` and the `post_id` to look up the `role_id` in the `user_post` table.  Then the method retrieves rows in the `role_permissions` table based on the `role_id`, obtains associated `capability_id` values, and refers to the `capability` table to retrieve capabilities associated with those `capability_id` values.  If "update_author_ids_of_post" is among the capabilities, then  `User.can_update_author_ids_of_post(post_id)` returns `True`.  

## Question 2 
### How would you have to change the PATCH route given your answer above to handle roles?

The route currently calls a function `/api/util/helpers_to_update_post.py/generate_updated_post_response(existing_post, parsed_json)`, which calls `/api/util/helpers_to_update_post.py/update_post(post, parsed_json)`.  Within the `update_post(post, parsed_json)` function, we check `if "authorIds" in parsed_json`.  If the request body does include `authorIds`, then the route additionally checks that the user making the request has access to edit the authors' list.  Here is where we use the aforementioned `User.can_update_author_ids_of_post(post_id)` method.

**Only if** this method returns `True`, the route proceeds to the rest of the flow processing updates to the authors' list, tags, and/or text of the post.  If not, give an **error message** with a 403 status code to the user.  Per REST best practices, 403 Forbidden is the appropriate code because we are refusing to authorize the request due to access that is tied to the application logic checking for sufficient rights.  We can have a dialogue with teammates to decide how specific the error messaging should be to both be secure and helpful.  Depending on the context, we simply let the user know that they do not have this capability, versus giving away precisely which role the user needs to have to get this capability, or explaining what the user's current capabilities include or exclude, because that could help a malicious actor make a series of requests and piece together information they should not know. 

### Flask RBAC module

Relevant documentation: [docs](https://flask-rbac.readthedocs.io/en/latest/)

Using this module would involve: 
- Set `Role` Model: 
  - Create a `Role` class that extends the `RoleMixin` provided by Flask-RBAC.
  - Perform overrides recommended in documentation to work with SQLAlchemy and support saving roles to the database. 
  - Define necessary fields, such as `id` and `name`.
  - If applicable in the future, establish relationships between roles using parent-child relationships.

- Set `User` Model: 
  - Extend the `UserMixin` provided by Flask-RBAC.
  - Perform overrides recommended in documentation to work with SQLAlchemy.
  - Establish a relationship between `User` and `Role` models, using a many-to-many relationship table to associate users with their roles. 

- Configure Flask-RBAC:
  - Set the role model by calling `rbac.set_role_model(Role)` to use the custom `Role` model.
  - Set the user model by calling `rbac.set_user_model(User)` to use the custom `User` model.

## Alternatives considered
I considered defining a capability as the capability to read a specific table, or to edit, delete, or create in a specific table.  Instead I chose an approach that allows for a capability to encompass multiple tables and/or operations.  Coupling permissions to database tables works well when the database directly models the domain.  However, we may want to express capabilities that do not fit that way, e.g., only allow `editor`s to send an email notification. 

## Adjacent concerns
Depending on the database we are using, there may be features of the database that we can take advantage of to help us govern access to tables.  For example, PostgreSQL's [row security policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) can restrict which rows a user can query, insert, update, or delete. 

Let's **audit** the role information.  Comprehensive logs of changes to the contents of the tables covered above will help us to observe inefficiencies and investigate evidence of security concerns.  Reporting on system vulnerability can become especially important to mitigate risks as the surface area over which permissions have to be managed grows and as roles proliferate.  As an extreme example, it would be alarming if all roles suddenly got access to create anything.  Also for instance, when there are two different roles that have the same permission set, it may be worthy to understand why that happened and whether we want to allow or monitor for that.  There should be guidelines in place so that if a role gets deprecated, we are aware of the impact on users and have scalable ways to potentially reassign users responsibly. 

#### Footnotes 

[^1]: There are implementations besides correlating a capability with a function.  For example, a capability can be at an API endpoint level - perhaps only users with role `editor` or `owner` for a post should have access to our PATCH route.  With capabilities being associated to functions, we will have to handle behaviors such as when engineers change function names. 

[^2]: We see that `role_id` `1` has capability of `capability_id` `1`, `2`, or `3` and we present this permission set in three rows instead of in one row where we associate this role_id with a value that is an array of the three capabilities.  This decision is because of an effort to normalize the schema as much as possible and better support query performance. 

[^3]: In this sample table, each user has one role in relation to a post.  If a user can simultaneously have multiple roles on a post - let's say if user with `user_id` `1` is an `owner` and a `fun_new_role`, where this role has `role_id == 4` on the post with `post_id` `1` - we can envision a row in the table of 1, 1, 1, which we already illustrate, and another row of 1, 1, 4. 