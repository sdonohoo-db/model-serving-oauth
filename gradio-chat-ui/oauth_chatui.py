from databricks.sdk.oauth import OAuthClient
from fastapi import FastAPI, Request, Depends
from starlette.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import gradio as gr
from gradio.themes.utils import sizes
import uvicorn
import os
import sys
import logging
import secrets
import requests

APP_NAME = "oauth_chatui"

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32))


# Callback route for authorization code/challenge exchange
@app.route('/callback')
async def callback(request: Request):
    """The callback route initiates consent using the OAuth client, exchanges
    the callback parameters, and redirects the user to the index page."""
    from databricks.sdk.oauth import Consent

    consent = Consent.from_dict(oauth_client, request.session.get("consent"))

    request.session["creds"] = consent.exchange_callback_parameters(request.query_params).as_dict()
    return RedirectResponse(url='/')

# index URL. First checks to see if OAuth credentials already exist in the session.
# If they do not, initiate consent process to get authorization
@app.get('/')
def index(request: Request):
    creds = request.session.get("creds")

    if creds is None:
        consent = oauth_client.initiate_consent()
        request.session["consent"] = consent.as_dict()
        return RedirectResponse(url=consent.auth_url)

    from databricks.sdk import WorkspaceClient
    from databricks.sdk.oauth import SessionCredentials

    credentials_provider = SessionCredentials.from_dict(oauth_client, creds)
    workspace_client = WorkspaceClient(host=oauth_client.host,
                                        product=APP_NAME,
                                        credentials_provider=credentials_provider,
                                        )
    
    # Get OAuth access token from session credentials
    access_token = creds.get("token").get("access_token")
    os.environ["API_TOKEN"] = access_token

    return RedirectResponse(url='/chatui')


##
## Gradio Chat UI Functions
##

# 
def respond(message, history):

    if len(message.strip()) == 0:
        return "ERROR the question should not be empty"

    local_token = os.getenv('API_TOKEN')
    endpoint_name = os.getenv('ENDPOINT_NAME')
    local_endpoint = f"{databricks_instance}/serving-endpoints/{endpoint_name}/invocations"

    if local_token is None or endpoint_name is None or local_endpoint is None:
        return "ERROR missing env variables"

    # Add your OAuth access token to the headers
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {local_token}'
    }

    # Set the payload with message to respond to
    q = {"inputs": [message]}

    try:
        response = requests.post(
            local_endpoint, json=q, headers=headers, timeout=100)
        response_data = response.json()
        response_data=response_data["predictions"][0]

    except Exception as error:
        response_data = f"ERROR status_code: {type(error).__name__}"

    return response_data

# Set size and look of chat window
theme = gr.themes.Soft(
    text_size=sizes.text_sm,radius_size=sizes.radius_sm, spacing_size=sizes.spacing_sm,
)

# Define main Gradio chat interface
with gr.ChatInterface(
    respond,
    chatbot=gr.Chatbot(show_label=False, container=False, show_copy_button=True, bubble_full_width=True),
    textbox=gr.Textbox(placeholder="Ask me a question",
                       container=False, scale=7),
    title="Databricks LLM RAG demo - Chat with DBRX Databricks model serving endpoint",
    description="This chatbot is a demo example for the dbdemos llm chatbot. <br>This content is provided as a LLM RAG educational example, without support. It is using DBRX, can hallucinate and should not be used as production content.<br>Please review our dbdemos license and terms for more details.",
    examples=[["What is DBRX?"],
              ["How can I start a Databricks cluster?"],
              ["What is a Databricks Cluster Policy?"],
              ["How can I track billing usage on my workspaces?"],],
    cache_examples=False,
    theme=theme,
    retry_btn=None,
    undo_btn=None,
    clear_btn="Clear",
) as chatui:
    chatui.load()

# Mount gradio app as a url path under fastapi with a dependency on authenticating through
# the root URL that checks for credentials
app = gr.mount_gradio_app(app, chatui, path="/chatui", auth_dependency=index)


def init_oauth_config(host, client_id, client_secret, port) -> OAuthClient:
    """Creates Databricks SDK configuration for OAuth"""
    oauth_client = OAuthClient(host=host,
                               client_id=client_id,
                               client_secret=client_secret,
                               redirect_url=f"http://localhost:{port}/callback",
                               # All three scopes needed for model serving on Azure
                               scopes=["all-apis", "offline_access", "user_impersonation"],
                               )
    if not oauth_client.client_id:
        print("Error: Application not registered.")

    # If authenticating to Azure, OAuthClient() drops all-apis scope needed. Add it back.
    # See PR https://github.com/databricks/databricks-sdk-py/pull/599
    #if oauth_client.is_azure():
    oauth_client._scopes.append("all-apis") 

    return oauth_client

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout,
                        level=logging.INFO,
                        format="%(asctime)s [%(name)s][%(levelname)s] %(message)s",
                        )
    logging.getLogger("databricks.sdk").setLevel(logging.DEBUG)

    # To execute, the following should be set in the application environment
    # ENDPOINT_NAME - name of the model serving endpoint the chat ui will use (ex: dbdemos_endpoint_main_rag_chatbot)
    # DATABRICKS_INSTANCE - URL of the Databricks instance hosting the endpoint and authenticating
    # CLIENT_ID - Client ID for this OAuth application as registered in the Databricks account
    # CLIENT_SECRET - Client secret for this OAuth application as registered in the Databricks account

    databricks_instance = os.getenv('DATABRICKS_INSTANCE')
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')
    port = 8000

    oauth_client = init_oauth_config(databricks_instance, client_id, client_secret, port)

    uvicorn.run(app)