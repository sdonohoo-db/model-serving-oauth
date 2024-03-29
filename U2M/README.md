# Querying a Model Serving Endpoint using U2M OAuth Authentication

These steps walk through the configuration needed for an application to query a Databricks model serving endpoint using U2M OAuth for authentication instead of a personal access token.

1. Create a Microsoft Entra ID App Registration
    Create an App registration for your application in Microsoft Entra ID.
    This manages the Entra ID login for your users to the application itself.

2. Install the [databricks cli](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/cli/install) and the [databricks python sdk](https://docs.databricks.com/en/dev-tools/sdk-python.html#get-started-with-the-databricks-sdk-for-python) in your Python environment. The databricks python sdk should be version `databricks-sdk-0.21.0` or later.

3. Create an Azure Databricks Account authentication profile. Choose a Databricks profile name (ex: `AzureAcct`). You will be prompted for your Azure Databricks account ID which you can obtain from your account console at [account.azuredatabricks.com](https://account.azuredatabricks.com).


    ```bash
    > databricks auth login https://accounts.azuredatabricks.net
    Databricks Profile Name: AzureAcct
    Databricks Account ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    Profile AzureAcct was successfully saved
    ```

4. Create an Azure Databricks OAuth Application Registration.  

    On Azure, this is done using the databricks CLI. Parameters needed:  
    * Name of the application to register. In this case, `flask_app_with_oauth`  
    * Redirect URL for your app that the OAuth server redirect back to. In our sample app, this is `http://localhost:5001/callback`. If you change the redirect url in you app, make sure this url matches.  
    * The list of OAuth scopes required for your application to access Databricks APIs. For model serving API access, `all-apis` is required. For endpoints on Azure Databricks, scopes `offline_access` and `user_impersonation` are required.

    ```shell
    > databricks account custom-app-integration create --confidential --json '{"name":"flask_app_with_oauth", "redirect_urls":[http://localhost:5001/callback], "scopes":["all-apis","offline_access","user_impersonation"]}' –-debug
    ```

    The output should be similar to the following:

    ```
    16:20:18  INFO start pid=6839 version=0.215.0 args="databricks, account, custom-app-integration, create, --confidential, --json, {\"name\":\"flask_app_with_oauth\", \"redirect_urls\":[\http://localhost:5001/callback\], \"scopes\":[\"all-apis\",\"offline_access\",\"user_impersonation\"]}, --debug"
    16:20:18 DEBUG Loading DEFAULT profile from /Users/scott.donohoo/.databrickscfg pid=6839 sdk=true
    16:20:18  INFO Ignoring pat auth, because databricks-cli is preferred pid=6839 sdk=true
    16:20:18  INFO Ignoring basic auth, because databricks-cli is preferred pid=6839 sdk=true
    16:20:18  INFO Ignoring oauth-m2m auth, because databricks-cli is preferred pid=6839 sdk=true
    16:20:18  INFO Refreshed OAuth token from Databricks CLI, expires on 2024-03-12 17:09:32.492687 -0400 EDT pid=6839 sdk=true
    16:20:18 DEBUG Using Databricks CLI authentication with Databricks OAuth tokens pid=6839 sdk=true
    16:20:18  INFO Refreshed OAuth token from Databricks CLI, expires on 2024-03-12 17:09:32.492687 -0400 EDT pid=6839 sdk=true
    16:20:18 DEBUG POST /api/2.0/accounts/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/oauth2/custom-app-integrations
    > {
    >   "confidential": true,
    >   "name": "flask_app_with_oauth",
    >   "redirect_urls": [
    >     "http://localhost:5001/callback"
    >   ],
    >   "scopes": [
    >     "all-apis",
    >     "offline_access",
    >     "user_impersonation"
    >   ]
    > }
    < HTTP/2.0 200 OK
    < {
    <   "client_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    <   "client_secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    <   "integration_id": "af59f1a9-37e2-4e2c-a86a-fb635ed7ecd7"
    < } pid=6839 sdk=true
    {
    "client_id":"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "client_secret":"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "integration_id":"af59f1a9-37e2-4e2c-a86a-fb635ed7ecd7"
    }
    16:20:18  INFO completed execution pid=6839 exit_code=0
    ```

    Make a note of the client_id and secret_id. Your application will need this information to request an OAuth token. The integration_id is needed only to make changes to or delete the application registration.

5. It is recommended to install and deploy the Quickstart scenario from the [Databricks RAG Chatbot solution accelerator](https://www.databricks.com/resources/demos/tutorials/data-science-and-ai/lakehouse-ai-deploy-your-llm-chatbot). This will create a model serving endpoint that the example client application is already set up to query. You may deploy the advanced scenario as well but the query schema will be different from the sample query in the application.  

6. Edit flask_app_with_oauth.py. This sample client app is an  adapted from https://github.com/databricks/databricks-sdk-py/blob/main/examples/flask_app_with_oauth.py to call a Databricks model serving endpoint.  

    Edit `DATABRICKS_INSTANCE` and `ENDPOINT_NAME` to match the Databricks workspace host and model serving endpoint in your RAG demo deployment.

    If you deployed the advanced scenario, also edit the JSON query payload, ‘data’, in the call_model_serving_endpoint() function to match its schema. You can find an example query json to copy/paste when you test query the endpoint in the Databricks serving UI.


7. Run the flask_app_with_oauth.py application using your databricks workspace url and the client_id and secret_id you collected from the output of the oauth app registration:

    ```bash
    > python flask_app_with_oauth.py https://<workspace-url>.azuredatabricks.net/ --client_id xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  --client_secret xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    ```

    Output should similar to:

    ```
    * Serving Flask app 'flask_app_with_oauth'
    * Debug mode: on
    2024-03-12 17:07:14,528 [werkzeug][INFO] WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
    * Running on http://localhost:5001
    2024-03-12 17:07:14,528 [werkzeug][INFO] Press CTRL+C to quit
    2024-03-12 17:07:14,528 [werkzeug][INFO]  * Restarting with stat
    2024-03-12 17:07:14,988 [werkzeug][WARNING]  * Debugger is active!
    2024-03-12 17:07:15,000 [werkzeug][INFO]  * Debugger PIN: 636-786-142
    ```
 

8. In your browser, visit http://localhost:5001 . You should be prompted to authenticate with Azure, then the application will authenticate to Databricks and call the endpoint.