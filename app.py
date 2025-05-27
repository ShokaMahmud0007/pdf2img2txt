from flask import Flask, render_template, request, send_file
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import os
import json
import zipfile
import re
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
IMAGE_FOLDER = os.path.join(UPLOAD_FOLDER, "images")
OUTPUT_FILE = os.path.join(UPLOAD_FOLDER, "output.json")
os.makedirs(IMAGE_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    extracted_text = ""
    json_output = ""
    show_download = False
    show_images = False
    download_links = []

    if request.method == 'POST':
        uploaded_files = request.files.getlist('image')
        selected_options = request.form.getlist('output_option')

        save_text = 'text' in selected_options
        save_json = 'json' in selected_options
        save_images = 'images' in selected_options

        all_lines = []

        for uploaded in uploaded_files:
            ext = os.path.splitext(uploaded.filename)[1].lower()
            file_id = str(uuid.uuid4())
            file_path = os.path.join(UPLOAD_FOLDER, f"{file_id}{ext}")
            uploaded.save(file_path)

            if ext == '.pdf':
                images = convert_from_path(file_path)
                for i, img in enumerate(images):
                    if save_images:
                        img_filename = f"{file_id}_page{i+1}.png"
                        img_path = os.path.join(IMAGE_FOLDER, img_filename)
                        img.save(img_path)
                        download_links.append(img_filename)
                    if save_text or save_json:
                        text = pytesseract.image_to_string(img, lang='eng+ben')
                        all_lines.extend(text.strip().splitlines())
            else:
                img = Image.open(file_path)
                if save_images:
                    img_filename = f"{file_id}.png"
                    img_path = os.path.join(IMAGE_FOLDER, img_filename)
                    img.save(img_path)
                    download_links.append(img_filename)
                if save_text or save_json:
                    text = pytesseract.image_to_string(img, lang='eng+ben')
                    all_lines.extend(text.strip().splitlines())

        extracted_text = "\n".join(all_lines)

        if save_json:
            formatted = []
            for line in all_lines:
                line = re.sub(r'^[\d\s:.\-]*', '', line)
                if "-" in line:
                    parts = line.split("-", 1)
                    formatted.append({"en": parts[0].strip(), "bn": parts[1].strip()})
            json_output = json.dumps(formatted, ensure_ascii=False, indent=4)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(json_output)
            show_download = True

        if save_images and download_links:
            zip_path = os.path.join(UPLOAD_FOLDER, "images.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for img_file in download_links:
                    full_path = os.path.join(IMAGE_FOLDER, img_file)
                    zipf.write(full_path, arcname=img_file)
            show_images = True

    return render_template('index.html',
                           text=extracted_text,
                           json_text=json_output,
                           show_download=show_download,
                           show_images=show_images)

@app.route('/download/json')
def download_json():
    return send_file(OUTPUT_FILE, as_attachment=True)

@app.route('/download/images')
def download_images():
    return send_file(os.path.join(UPLOAD_FOLDER, "images.zip"), as_attachment=True)

if __name__ == '__main__':
    app.run()
