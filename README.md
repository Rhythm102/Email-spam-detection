# Email-spam-detection
AI-Powered Email Classifier
A full-stack web application that leverages Naive Bayes, a powerful Machine Learning algorithm, to classify emails as either Spam or Ham (Safe). This tool is specifically designed to identify modern phishing attempts and social engineering tactics that traditional keyword-based filters often miss.

🚀 Live Demo: https://email-spam-detection-law1.onrender.com/

## Overview
Nowadays, scammers use sophisticated language and Generative AI to bypass standard email security. This project provides a deep-learning-based defense mechanism that analyzes the intent and context of an email rather than just looking for "blacklisted" words.

Why Use This AI Detector?
Deep Semantic Analysis: Understands the tone and urgency of the message to identify hidden threats.

Zero-Day Protection: Detects brand-new scam patterns by recognizing suspicious behavioral traits.

Combatting AI-Generated Scams: Identifies robotic patterns in text written by LLMs (like GPT-4) used by hackers.

## Tech Stack
Frontend: HTML5, CSS3 (Glassmorphism & Responsive Design), JavaScript (ES6+).

Backend: Python, Flask.

Machine Learning: Scikit-learn (Naive Bayes), NLTK.

Deployment: Render.

## Project Structure

- **static/**  
  - CSS, images, and background assets
- **templates/**  
  - HTML files (index.html)
- **app.py**  
  - Main Flask server
- **spam_classifier.ipynb**  
  - Model training & EDA notebook
- **model.pkl**  
  - Trained ML model
- **vectorizer.pkl**  
  - Text processing vectorizer
- **requirements.txt**  
  - Project dependencies
- **README.md**  
  - Documentation
