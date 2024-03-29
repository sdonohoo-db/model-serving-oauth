#!env python3
""" Flask with OAuth:

This application provides end-to-end demonstration of Databricks SDK for Python
capabilities of OAuth Authorization Code flow with PKCE security enabled. This
can help you build a hosted app with every user using their own identity to
access Databricks resources.

If you have already Custom App:

./flask_app_with_oauth.py <databricks workspace url> \
    --client_id <app-client-id> \
    --client_secret <app-secret> \
    --port 5001

If you want this script to register Custom App and redirect URL for you:

./flask_app_with_oauth.py <databricks workspace url>

You'll get prompted for Databricks Account username and password for
script to enroll your account into OAuth and create a custom app with
http://localhost:5001/callback as the redirect callback. Client and
secret credentials for this OAuth app will be printed to the console,
so that you could resume testing this app at a later stage.

Once started, please open http://localhost:5001 in your browser and
go through SSO flow to execute your test query against the model
serving endpoint.
"""

import argparse
import logging
import sys
import requests

from databricks.sdk.oauth import OAuthClient

APP_NAME = "flask_app_with_oauth"
DATABRICKS_INSTANCE = 'xxxxxxxxx.azuredatabricks.net'  # Set your Databricks instance host here
ENDPOINT_NAME = 'dbdemos_endpoint_main_rag_chatbot' # Change to the name of your model serving endpoint


def call_model_serving_endpoint(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'  # Explicitly set Content-Type to application/json
    }

    # Example API call to the model serving endpoint
    api_url = f"https://{DATABRICKS_INSTANCE}/serving-endpoints/{ENDPOINT_NAME}/invocations"

    # Note: endpoint query schema matches quickstart deployment scenario in the demo at
    # https://www.databricks.com/resources/demos/tutorials/data-science-and-ai/lakehouse-ai-deploy-your-llm-chatbot
    data = {
        "dataframe_split": {
            "columns": [
                "query"
            ],
            "data": [
                [
                    "How can I track billing usage on my workspaces?"
                ]
            ]
        }
    }
    response = requests.post(api_url, json=data, headers=headers, timeout=100)

    if response.status_code != 200:
        raise Exception(f'Request failed with status {response.status_code}, {response.text}')
    
    return response.json()


def create_flask_app(oauth_client: OAuthClient, port: int):
    """The create_flask_app function creates a Flask app that is enabled with OAuth.

    It initializes the app and web session secret keys with a randomly generated token. It defines two routes for
    handling the callback and index pages.
    """
    import secrets

    from flask import (Flask, redirect, render_template_string, request,
                       session, url_for)

    app = Flask(APP_NAME)
    app.secret_key = secrets.token_urlsafe(32)

    @app.route("/callback")
    def callback():
        """The callback route initiates consent using the OAuth client, exchanges
        the callback parameters, and redirects the user to the index page."""
        from databricks.sdk.oauth import Consent

        consent = Consent.from_dict(oauth_client, session["consent"])

        session["creds"] = consent.exchange_callback_parameters(request.args).as_dict()
        return redirect(url_for("index"))

    @app.route("/")
    def index():
        """The index page checks if the user has already authenticated and retrieves the user's credentials using
        the Databricks SDK WorkspaceClient. It then renders the template with the clusters' list."""
        if "creds" not in session:
            consent = oauth_client.initiate_consent()
            session["consent"] = consent.as_dict()
            return redirect(consent.auth_url)

        from databricks.sdk import WorkspaceClient
        from databricks.sdk.oauth import SessionCredentials

        credentials_provider = SessionCredentials.from_dict(oauth_client, session["creds"])
        workspace_client = WorkspaceClient(host=oauth_client.host,
                                           product=APP_NAME,
                                           credentials_provider=credentials_provider,
                                           )
        
        # Get OAuth access token from session credentials
        access_token = session["creds"]["token"]["access_token"]

        return call_model_serving_endpoint(access_token)

    return app


def register_custom_app(oauth_client: OAuthClient, args: argparse.Namespace) -> tuple[str, str]:
    """Creates new Custom OAuth App in Databricks Account"""

    logging.info("No OAuth custom app client/secret provided, creating new app")

    import getpass

    from databricks.sdk import AccountClient

    account_client = AccountClient(host="https://accounts.cloud.databricks.com",
                                   account_id=input("Databricks Account ID: "),
                                   username=input("Username: "),
                                   password=getpass.getpass("Password: "),
                                   )

    custom_app = account_client.custom_app_integration.create(
        name=APP_NAME, redirect_urls=[f"http://localhost:{args.port}/callback"], confidential=True,
        scopes=["all-apis","offline_access","user_impersonation"],
    )
    logging.info(f"Created new custom app: "
                 f"--client_id {custom_app.client_id} "
                 f"--client_secret {custom_app.client_secret}")

    return custom_app.client_id, custom_app.client_secret


def init_oauth_config(args) -> OAuthClient:
    """Creates Databricks SDK configuration for OAuth"""
    oauth_client = OAuthClient(host=args.host,
                               client_id=args.client_id,
                               client_secret=args.client_secret,
                               redirect_url=f"http://localhost:{args.port}/callback",
                               # All three scopes needed for model serving on Azure
                               scopes=["all-apis", "offline_access", "user_impersonation"],
                               )
    if not oauth_client.client_id:
        client_id, client_secret = register_custom_app(oauth_client, args)
        oauth_client.client_id = client_id
        oauth_client.client_secret = client_secret

    return oauth_client


def parse_arguments() -> argparse.Namespace:
    """Parses arguments for this demo"""
    parser = argparse.ArgumentParser(prog=APP_NAME, description=__doc__.strip())
    parser.add_argument("host")
    for flag in ["client_id", "client_secret"]:
        parser.add_argument(f"--{flag}")
    parser.add_argument("--port", default=5001, type=int)
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout,
                        level=logging.INFO,
                        format="%(asctime)s [%(name)s][%(levelname)s] %(message)s",
                        )
    logging.getLogger("databricks.sdk").setLevel(logging.DEBUG)

    args = parse_arguments()
    oauth_cfg = init_oauth_config(args)

    # Workaround for bug in databricks-sdk-py oauth.py
    # Scopes incomplete for calling model serving on Azure.
    # See PR https://github.com/databricks/databricks-sdk-py/pull/599
    oauth_cfg._scopes.append("all-apis")
    
    app = create_flask_app(oauth_cfg, args.port)

    app.run(
        host="localhost",
        port=args.port,
        debug=True,
        # to simplify this demo experience, we create OAuth Custom App for you,
        # but it intervenes with the werkzeug reloader. So we disable it
        use_reloader=args.client_id is not None,
    )
