# Gradio Chatbot Interface using U2M OAuth Authentication

This example application demonstrates using OAuth to authenticate to Databricks and call a model serving endpoint as part of a RAG Chatbot scenario. It is a Gradio chatbot application wrapped in a FastAPI application for session management. 

It is adapted from the sample Gradio UI included with the RAG Chatbot Demo, [Deploy Your LLM Chatbot With Retrieval Augmented Generation (RAG), DBRX Instruct Foundation Models and Vector Search](https://www.databricks.com/resources/demos/tutorials/data-science-and-ai/lakehouse-ai-deploy-your-llm-chatbot) which uses a Personal Access Token for authentication.

### To Run the Application

1. Install the RAG Chatbot demo linked above and create a model serving endpoint. The application code can easily be modified to call other model endpoints but this is recommended for testing.

2. Register a custom OAuth application in the Databricks account console following the instructions [here](https://docs.databricks.com/en/integrations/enable-disable-oauth.html#enable-custom-oauth-applications-using-the-databricks-ui). When creating the registration, specify the following:  
    * Redirect URL: 'http://localhost:8000/callback'. If you modify this URL, be sure to make the corresponding change, whether port or path, in the code.
    * Select 'All APIs' for Access scopes.
    * Check 'Generate a client secret'  

    When adding the new registration, be certain to note the **client_id** and **client_secret**. You will need these to run the application.

3. Navigate to the deployed model serving endpoint in the Databricks workspace hosting the endpoint and select 'Permissions' in the upper-right. Ensure that your Databricks userid has 'Can Query' permission on the endpoint.

4. In the application environment, export the following environment variables needed to run the application:  

    **ENDPOINT_NAME**=\<model serving endpoint name\>    Ex: dbdemos_endpoint_main_rag_chatbot  
    **DATABRICKS_INSTANCE**=\<URL of the Databricks instance hosting the endpoint\>  
    **CLIENT_ID**=\<Client ID for this application as registered in the Databricks account\>  
    **CLIENT_SECRET**=\<Client Secret for this application as registered in the Databricks account\> 

5. Run the application:  

    `# python oauth_chatui.py`

    Open a browser tab to http://localhost:8000

    If you are not currently authenticated to the Databricks workspace, you should be prompted to authenticate. On successfull authenticatio, you will be redirected to the Gradio Chat UI.