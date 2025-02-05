from flask import Flask, request, jsonify  # type:ignore
import os
import time
import threading
from io import BytesIO

import google.generativeai as genai  # type:ignore
import pyaudio  # type:ignore
import speech_recognition as sr  # type:ignore
from PIL import Image  # type:ignore
import requests  # type:ignore
from PyPDF2 import PdfReader  # type:ignore
from dotenv import load_dotenv  # type:ignore
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

chat_session = model.start_chat(history=[])

loading = True

def display_loading():
    start_time = time.time()
    while loading:
        elapsed_time = time.time() - start_time
        seconds = int(elapsed_time)
        milliseconds = int((elapsed_time - seconds) * 1000)
        print(f"Generating response... {seconds}.{milliseconds:03d} seconds elapsed", end='\r')
        time.sleep(0.1)

def get_response(session, input_text):
    global loading
    loading = True
    loading_thread = threading.Thread(target=display_loading)
    loading_thread.start()
    response = session.send_message(input_text)
    loading = False
    loading_thread.join()
    print("\nResponse received.")
    return response.text

def recognize_speech_from_mic():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Listening for your query...")
        audio = recognizer.listen(source)
    try:
        print("Recognizing speech...")
        text = recognizer.recognize_google(audio)
        print(f"Recognized text: {text}")
        return text
    except sr.UnknownValueError:
        return "Sorry, I did not understand that."
    except sr.RequestError:
        return "Sorry, there was an error with the speech recognition service."

def read_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def generate_image(prompt):
    url = "https://api.gemini.ai/image/generate"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "prompt": prompt,
        "image_size": "512x512"
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        image_data = response.content
        with open("generated_image.png", "wb") as f:
            f.write(image_data)
        image = Image.open(BytesIO(image_data))
        image.show()
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")

def summarize_audio(file_path):
    your_file = genai.upload_file(path=file_path)
    prompt = "Listen carefully to the following audio file. Provide a brief summary."
    response = model.generate_content([prompt, your_file])
    return response.text

def analyze_video(file_path):
    print(f"Uploading file: {file_path}")
    video_file = genai.upload_file(path=file_path)
    print(f"Completed upload: {video_file.uri}")

    while video_file.state.name == "PROCESSING":
        print('Waiting for video to be processed.')
        time.sleep(10)
        video_file = genai.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise ValueError(video_file.state.name)
    
    print(f'Video processing complete: {video_file.uri}')

    prompt = "Describe this video."

    model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")

    print("Making LLM inference request...")
    response = model.generate_content([prompt, video_file], request_options={"timeout": 600})
    return response.text

def fitness_support(input_text):
    fitness_model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction="You are a fitness expert. Ask the user for their age, weight, height, fitness goals, and any other relevant information to provide personalized fitness advice. After giving instructions or diet plans, ask follow-up questions to refine your advice."
    )
    fitness_session = fitness_model.start_chat(history=[])
    response_text = get_response(fitness_session, input_text)
    return response_text

def mental_health_support(input_text):
    mental_health_model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction="You are a mental health support expert. Be very empathetic and very polite. Ask the user how they are feeling and provide supportive advice."
    )
    mental_health_session = mental_health_model.start_chat(history=[])
    response_text = get_response(mental_health_session, input_text)
    return response_text

def general_health_support(input_text):
    general_health_model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction="You are a doctor. Provide professional medical advice based on the user's symptoms and questions."
    )
    general_health_session = general_health_model.start_chat(history=[])
    response_text = get_response(general_health_session, input_text)
    return response_text

def financial_management_support(input_text):
    financial_management_model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction="You are a financial management expert. Help the user in tracking their income, provide insights based on their expenses and income, and recommend actions based on their inputs. Ask for details about their financial goals, monthly income, expenses, and savings."
    )
    financial_management_session = financial_management_model.start_chat(history=[])
    response_text = get_response(financial_management_session, input_text)
    return response_text

def personalized_assistance(input_text):
    personalized_assistance_model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction="You are a personal assistant. Understand the user's preferences, talk like a friend, give tailored recommendations, assist with personal tasks such as itinerary planning and shopping lists, and offer relevant recommendations."
    )
    personalized_assistance_session = personalized_assistance_model.start_chat(history=[])
    response_text = get_response(personalized_assistance_session, input_text)
    return response_text

@app.route('/text', methods=['POST'])
def handle_text():
    data = request.json
    input_text = data.get('text')
    response_text = get_response(chat_session, input_text)
    return jsonify({'response': response_text})

@app.route('/voice', methods=['POST'])
def handle_voice():
    input_text = recognize_speech_from_mic()
    response_text = get_response(chat_session, input_text)
    return jsonify({'response': response_text})

@app.route('/pdf', methods=['POST'])
def handle_pdf():
    pdf_file = request.files['file']
    file_path = os.path.join("/tmp", pdf_file.filename)
    pdf_file.save(file_path)
    input_text = read_pdf(file_path)
    response_text = get_response(chat_session, input_text)
    return jsonify({'response': response_text})

@app.route('/image', methods=['POST'])
def handle_image():
    data = request.json
    prompt = data.get('prompt')
    generate_image(prompt)
    return jsonify({'response': 'Image generated successfully.'})

@app.route('/audio', methods=['POST'])
def handle_audio():
    audio_file = request.files['file']
    file_path = os.path.join("/tmp", audio_file.filename)
    audio_file.save(file_path)
    response_text = summarize_audio(file_path)
    return jsonify({'response': response_text})

@app.route('/video', methods=['POST'])
def handle_video():
    video_file = request.files['file']
    file_path = os.path.join("/tmp", video_file.filename)
    video_file.save(file_path)
    response_text = analyze_video(file_path)
    return jsonify({'response': response_text})

@app.route('/health', methods=['POST'])
def handle_health():
    data = request.json
    support_type = data.get('support_type')
    input_text = data.get('text')

    if support_type == 'fitness':
        response_text = fitness_support(input_text)
    elif support_type == 'mental_health':
        response_text = mental_health_support(input_text)
    elif support_type == 'general_health':
        response_text = general_health_support(input_text)
    else:
        return jsonify({'error': 'Invalid support type'}), 400

    return jsonify({'response': response_text})

@app.route('/financial', methods=['POST'])
def handle_financial():
    data = request.json
    input_text = data.get('text')
    response_text = financial_management_support(input_text)
    return jsonify({'response': response_text})

@app.route('/personalized', methods=['POST'])
def handle_personalized():
    data = request.json
    input_text = data.get('text')
    response_text = personalized_assistance(input_text)
    return jsonify({'response': response_text})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
