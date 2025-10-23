from fastapi import FastAPI
import gradio as gr
from text_to_sql import get_response
import os
#fastAPI initailize
app=FastAPI()

#connect gradio with fastAPI
def chat_interface(user_input):
    return get_response(user_input)

#Gradio Interface setup
ui=gr.Interface(
    fn=chat_interface,
    inputs=gr.Textbox(label="Ask your recipe question"),
    outputs="markdown",
    title="Text-to-SQL Recipe Assistant",
    description="Ask me anything about recipes! I'll query the database and show results, or generate one if not found."
)
#mount gradio ui inside the fastapi
app=gr.mount_gradio_app(app,ui,path="/ui")

#root endpoint
@app.get("/")
def home():
    return{"message": "Text-to-SQL Recipe Assistant running!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__=="__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000)) 
    uvicorn.run(app, host="0.0.0.0", port=port)