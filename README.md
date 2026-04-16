# AI Medical Recommendation System

A Flask-based web application that provides clinical-grade healthcare diagnosis predictions using Machine Learning (SVC) and maintains persistent records using Google Firebase Firestore.

## 🚀 Features
- **AI Diagnosis**: Predicts diseases based on user-entered symptoms using a trained ML model.
- **Firebase Backend**: Securely stores user profiles and prediction history in the cloud.
- **Admin Dashboard**: Comprehensive management interface for registered users and diagnosis records.
- **Export to Excel**: Users can download their medical history as an Excel file.
- **Modern UI**: Clean, glassmorphism-inspired design with a professional healthcare aesthetic.

## 🛠️ Technology Stack
- **Backend**: Python, Flask
- **Database**: Google Firebase Firestore (NoSQL)
- **Machine Learning**: Scikit-learn (SVC Model), Pandas, NumPy
- **Frontend**: HTML5, Vanilla CSS, FontAwesome

## 📋 Prerequisites
- Python 3.10+
- A Google Firebase Project

## ⚙️ Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sc23cs301030-pixel/Medical-Recommendation-System.git
   cd Medical-Recommendation-System
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Firebase Configuration**:
   - Go to your [Firebase Console](https://console.firebase.google.com/).
   - Download your `serviceAccountKey.json` from **Project Settings > Service Accounts**.
   - Place the file in the root directory of this project.

4. **Run the Application**:
   ```bash
   python main.py
   ```
   The app will be available at `http://127.0.0.1:5000`.

## 🔒 Security
The project is configured with a `.gitignore` to ensure that sensitive files like `serviceAccountKey.json` and local environments are **not** uploaded to public repositories.

## 👥 Admin Access
To create an admin account, use the **Admin Secret** during registration: `ADMIN123`.
