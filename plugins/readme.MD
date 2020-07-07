This is the Appfrican Plugin Section
- The entire folder is loaded onto the flask instance using a plugin, so anything that is created from here is automatically added.
- Plugins are created with basic information, 
    - Plugin Name
    - Version
    - author
    - blueprint (for routing and browsing)
    - prefix (e.g /my_plugin where the blueprint routes will be accessed)

To develop plugins, there are some extra variable added to the database for analysis and done after plugin is tested and integrated.

How Plugins are accessed by users.
- Each user has a user_id (hashed and accessible from session['user_id'] when logged in)
- When a user subscribes or registers for a service (after all payments are registration are done), the are taken to a plugin setup page
- Each plugin setup page will always generate a user_token (equivalent of an API key) and save it in both the plugin database and the main user database.
- The API token, randomly and uniquely generated will make it easy to track the user account of a person from the plugin side.

MUST REQUIREMENTS
- Use base template as provided on the __init__.py file of the plugin
- Use the subscriptions decorator to ensure proper access
- Use unique prefix to access the service
- Use login_required decorator on routes to ensure that the plugin runs with only authenticated users.

Provided Super-Classes 
---> These are classes and functions from the main code for various functions you might need to do in your plugin. You can check most in the functions.py sections.
- db function for database access. Getting main database data
- get_token and set_token for decoding session tokens
- dbname is database name for the main database, it varies sometimes since we are using a sandbox environment and other times we are using production. It can be changed from the main config.json file
- servdb is a quick mysql helper that is optional to use too
- mp is for mixpanel analytics tracking