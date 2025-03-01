from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
import requests
import uvicorn
import PyPDF2
import docx

app = FastAPI()
OLLAMA_API = "http://localhost:11434/api/generate"
DOCUMENT_TEXT = ""  


def extract_text_from_pdf(pdf_file):
    text = ""
    reader = PyPDF2.PdfReader(pdf_file)
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def extract_text_from_docx(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs])

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    global DOCUMENT_TEXT
    if file.filename.endswith(".pdf"):
        DOCUMENT_TEXT = extract_text_from_pdf(file.file)
    elif file.filename.endswith(".docx"):
        DOCUMENT_TEXT = extract_text_from_docx(file.file)
    elif file.filename.endswith(".txt"):
        DOCUMENT_TEXT = (await file.read()).decode("utf-8")
    else:
        return {"error": "Unsupported file format. Use PDF, TXT, or DOCX."}
    
    return {"message": "Document uploaded successfully", "word_count": len(DOCUMENT_TEXT.split())}


@app.post("/chat")
def chat(request: dict):
    global DOCUMENT_TEXT
    if not DOCUMENT_TEXT:
        return {"response": "No document uploaded. Please upload a document first."}
    
    user_query = request["message"]

    
    prompt = f"Using this document: {DOCUMENT_TEXT[:2000]}... Answer this question: {user_query}"

  
    payload = {
        "model": "deepseek-r1:1.5b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.9,  
            "top_p": 0.6,       
            "top_k": 10         
        }
    }
    
    response = requests.post(OLLAMA_API, json=payload)
    return {"response": response.json().get("response", "No response from model")}


@app.get("/", response_class=HTMLResponse)
def serve_html():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Document-Based Chatbot</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; }
            #chatbox { border: 1px solid #ccc; padding: 10px; height: 300px; overflow-y: auto; margin-bottom: 10px; }
            input, button { padding: 10px; margin-top: 10px; }
        </style>
    </head>
    <body>
        <h2>Chat with Your Document</h2>
        <input type="file" id="fileInput">
        <button onclick="uploadFile()">Upload</button>
        <p id="uploadStatus"></p>
        <div id="chatbox"></div>
        <input type="text" id="userInput" placeholder="Ask a question...">
        <button onclick="sendMessage()">Send</button>

        <script>
            async function uploadFile() {
                let fileInput = document.getElementById("fileInput").files[0];
                if (!fileInput) {
                    alert("Please select a file first.");
                    return;
                }
                
                let formData = new FormData();
                formData.append("file", fileInput);

                let response = await fetch("/upload", { method: "POST", body: formData });
                let result = await response.json();
                document.getElementById("uploadStatus").innerText = result.message;
            }

            async function sendMessage() {
                let userInput = document.getElementById("userInput").value;
                if (!userInput) return;

                let chatbox = document.getElementById("chatbox");
                chatbox.innerHTML += "<p><b>You:</b> " + userInput + "</p>";
                document.getElementById("userInput").value = "";

                let response = await fetch("/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: userInput })
                });

                let data = await response.json();
                chatbox.innerHTML += "<p><b>Bot:</b> " + data.response + "</p>";
                chatbox.scrollTop = chatbox.scrollHeight;
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
