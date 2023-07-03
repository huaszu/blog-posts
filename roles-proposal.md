# Roles

1. What database changes would be required to the starter code to allow for different roles for authors of a blog post? Imagine that we’d want to also be able to add custom roles and change the permission sets for certain roles on the fly without any code changes.

Given the scoping of this request from the product team, let's assume that we are concerned with managing what a user can do on a blog post when the user is an author of that post.  We assume that we are solving for places in the code where there is already or will be code that checks that a user is an author of a post - given that, we are now figuring out how to guide what a particular author can do.  We could make changes to enable the database to keep track of what roles are possible, what each role's permission set is, and which roles each author has.  In one potential implementation, 

- We could introduce a `role` table that keeps track of what each role's permission set is.  In this implementation, we focus on permission to read, edit, create, or delete records in tables in the database.  To start, `owner`, `editor`, and `viewer` can be example roles, per the question prompt.  In this sample, if we look at the `create` column for the record for `owner`, an owner can create a new association between a user and a post in the `user_post` table, meaning that an owner can add a user as an author of a post.  To meet the product requirement that **only owners of a blog post can modify the authors' list to a blog post (adding more authors, changing their role)**, an excerpt of the `role` table could look like: 

| role_id         | role_name       | read             | edit             | create           | delete           |
|-----------------|-----------------|------------------|------------------|------------------|------------------|
| 1               | owner           | [user_post, post]| [user_post, post]| [user_post, post]| [user_post, post]|   
| 1               | editor          | [post]           | [post]           | []               | []               |    
| 1               | viewer          | [post]           | []               | []               | []               |  

I considered having names of tables as columns - instead of having capabilities as columns `read`, `edit`, `create`, and `delete` - in which case values could be an array indicating a role's capabilities in relation to each table.  However, this other way makes less sense if there are more and more tables to regulate access for and we keep having to add columns to the `role` table. 

Given that this implementation represents access at a table level, we should enforce that the values for `read`, `edit`, `create`, and `delete` can only include elements that are the string name of a database table.  An aside: depending on the database we are using, there may be features of the database that we can take advantage of to help us govern access to tables. 

Since we care about ability to **add custom roles and change the permission sets for certain roles on the fly**, I decided to go with a separate `role` table that represents each role's permission set, and assigning each user a role in relation to each post, as opposed to more manually setting each user's permissions.  In the `role` table, we can add or delete roles and we can change the permission set of a role. 

Especially if roles proliferate, we may want to monitor this table so that we observe inefficiences and evidence of security concerns.  It would be alarming if all roles suddenly got access to create anything.  Also for instance, when there are two different role records that have the same permission set, it may be worthy to investigate why that happened and whether we want to allow for that.  There should be guidelines in place so that if a role gets deprecated, how do we treat the impact on users and have scalable ways to potentially reassign users responsibly? 

A modification on this implementation could be to have an additionally separate `permission` table, which has all of the possible permissions.  Then the `role` table could have columns `role_id`, `role_name`, and `permission_set`, where a value for `permission_set` could for example be `[1, 2]` to show that the role has permissions `1` and `2` from the  `permission` table.  An excerpt of the `permission` table could look like:

| permission_id | table_name    | capability    |       
|---------------|---------------|---------------|
| 1             | user_post     | read          |
| 2             | user_post     | edit          |

This alternative could help with easy visibility into what all of the possible permissions that exist are and potentially reporting on system vulnerability on a permission level, especially as the surface area over which permissions have to be managed grows.  We could speak with business stakeholders on the needs.  Of course, any change we make to the structure of database tables can affect how we write the code that traverses tables to get the intended information, such as code that checks whether a user has the permission to take an action or not.  

- We could add a column to the `user_post` table that indicates the role of each user for each associated post.  This design is because we want to allow the same user to have different roles depending on which post is at hand.  A user can be only a viewer of one blog post while being an owner of a different blog post.  Here is how this suggested change to the `user_post` table could look:

| user_id      | post_id       | user_role    |
|--------------|---------------|--------------|
| 1            | 1             | owner        |
| 2            | 1             | owner        |
| 2            | 2             | editor       |
| 2            | 3             | editor       |
| 3            | 3             | editor       |
| 3            | 4             | viewer       |

We are assuming that each user has one role in relation to a post.  If we foresee that a user may simultaneously need multiple roles, we can make the value for `user_role` be an array of roles. 

We may want to enforce that every record have a non-null value for `user_role`.  For example, at the point of `user_post` record creation, we could set a default that the `user_role` is `viewer` and offer ability to indicate a different role.  Depending on the role of the user who is wanting to indicate a different role, there may be limits on what roles we allow that user to give out.  We can speak with business and user experience stakeholders about the business logic - for example, if a user originated a post, perhaps this user should automatically be given an `owner` role for that post, which is one way to address the product requirement that **for any blog post, there must always be at least one owner of the blog post.**  In this solution, the program that adds a new post record to the `post` table and makes the pertinent updates to the `user_post` table could make that `owner` assignment to that user. There may be nuances, such as additional logic that initially makes this user's role `editor` and upgrades the role to `owner`, depending on whether or not the user has also verified their email or identity or taken other actions relevant to the business context. 

Let's require that the value for `user_role` be from among the roles in the `role` table.  If at the point of `user_role` assignment, a user wants to create an entirely new role, we can plan for the circumstances when that should or should not be enabled in our business context and put in place a process or tooling that considers security and the user experience. 

2. How would you have to change the PATCH route given your answer above to handle roles?

If the request body includes `authorIds`, then the route should check that the user making the request has access to edit the authors' list.  After the existing code that validates that the user is an author of the post, we need code that looks up in the `user_post` table the user making the request by `user_id` and the post the request is for by `post_id` and finds out what `user_role` is at play for this user for this post.  

In the existing code that updates the authors' list of a post - lines 30-41 in `/repository_layer/database_operations.py` - we call a function defined above on lines 18-21 that deletes from the `user_post` table and a function on lines 24-27 that creates in the `user_post` table.  We can add code that looks up the user role in the `role` table.  Before our program makes a change to the `user_post` table, the program should check whether the user role has access to make that change.  Specifically, is `user_post` one of the elements in the array of the `delete` value for that user role?  Is `user_post` one of the elements in the array of the `create` value for that user role?  While `user_post` shows up as a string in such an array, the connection between this string and the `user_post` table itself is that our model includes `__tablename__ = "user_post"` in the definition. 

Only if the access control allows, the route should proceed to the next step.  If not, give an error message with a 403 status code to the user.  Per REST best practices, 403 Forbidden is the appropriate code because we are refusing to authorize the request due to access that is tied to the application logic checking for sufficient rights.  We can have a dialogue with teammates to decide how specific the error messaging should be to both be secure and helpful.  Depending on the context, we may not want to give away precisely which role the user needs to have to get this capability, or explain what the user's current capabilities include or exclude, but simply let the user know that they do not have this capability. 

In the case that the access control does allow us to proceed, we need to add a check because **for any blog post, there must always be at least one owner of the blog post**.  Among the `authorIds` array in the request body, check in the `user_post` table that at least one is a `user_id` with `user_role == "owner"` for the `post_id` at hand.  If not, that means going through with the request would make the post have no owners so we should reject the request and return an error message with a 400 status code.  Again, we can have conversation with teammates to decide how specific the error messaging should be to both be secure and helpful.  Depending on the context, we may not want to give away exactly that, of the `authorIds` in the request, none have `user_role` of `owner`, because someone could make a series of requests to identify who the owners are - could be an overbearing concern for simple blog posts but bringing it up as a point that can matter in context.  We could let the user know that the server understood the request and is not processing the update to the authors' list. 

If the requested change does not break the rule that there must always be at least one owner of a post, then the code can progress to work on the rest of the flow updating the authors' list, tags, and/or text of the post. 


As a note, the proposal is more from a perspective of role-based access control, rather than attribute-based access control.  While I can imagine use cases in which we want granularity such that, for instance, a user can edit the `text` of a post but not the `reads` of a post, this is a different, though interconnected, problem from what the product team is coming to us now for. 