import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, send_file
from io import BytesIO
import matplotlib
matplotlib.use('Agg')  # Use 'Agg' backend for non-GUI environments
import matplotlib.pyplot as plt
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

class ArticleExtractor:
    def __init__(self):
        self.extracted_articles = []

    def extract_article_text(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an error for bad responses
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove all script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get the article title
            title = soup.find('h1').get_text() if soup.find('h1') else "No Title Found"

            # Get the article text
            article_text = ''
            for p in soup.find_all('p'):
                article_text += p.get_text() + '\n\n'

            return title, article_text

        except Exception as e:
            logging.error(f"Error extracting text from {url}: {e}")
            return None, None

    def extract_articles(self, df):
        self.extracted_articles = []
        for index, row in df.iterrows():
            url_id = row['URL_ID']
            url = row['URL']

            title, text = self.extract_article_text(url)

            if title and text:
                self.extracted_articles.append({
                    'url_id': url_id,
                    'title': title,
                    'text': text
                })

# Initialize the extractor
extractor = ArticleExtractor()

@app.route('/extract', methods=['POST'])
def extract_articles():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected.'}), 400

    try:
        df = pd.read_excel(file)

        # Validate required columns
        required_columns = ['URL_ID', 'URL']
        if not all(col in df.columns for col in required_columns):
            return jsonify({'error': 'Excel file must contain URL_ID and URL columns.'}), 400

        extractor.extract_articles(df)
        return jsonify(extractor.extracted_articles), 200
    except Exception as e:
        logging.error(f"Error processing file: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/visualize', methods=['POST'])
def visualize_data():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected.'}), 400

    column_name = request.form.get('column_name')
    if not column_name:
        return jsonify({'error': 'Column name not provided.'}), 400

    try:
        df = pd.read_excel(file)

        # Check if the column exists in the DataFrame
        if column_name not in df.columns:
            return jsonify({'error': f'Column "{column_name}" not found in the file.'}), 400

        plt.figure(figsize=(10, 6))
        df[column_name].value_counts().plot(kind='bar', color='skyblue')
        plt.title(f'Bar Chart of {column_name}')
        plt.xlabel('Categories')
        plt.ylabel('Frequency')

        # Save the plot to a BytesIO object
        img = BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        plt.close()

        return send_file(img, mimetype='image/png', as_attachment=True, download_name='visualization.png')
    except Exception as e:
        logging.error(f"Error visualizing data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def home():
    return "Welcome to the Jmedia Extractor and Visualizer API! Use the /extract and /visualize endpoints."

if __name__ == '__main__':
    app.run(debug=True)
