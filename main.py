import os
from flask import Flask, request, render_template, jsonify, redirect, url_for, flash, send_file
import numpy as np
import pandas as pd
import pickle
import firebase_admin
from firebase_admin import credentials, firestore
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import io
import json

# flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-very-secret-key-123')

# Initialize Firebase
try:
    # 1. Check for Environment Variable (for Render/Deployment)
    firebase_config = os.getenv('FIREBASE_CONFIG_JSON')
    
    if firebase_config:
        # Initialize from JSON string
        config_dict = json.loads(firebase_config)
        cred = credentials.Certificate(config_dict)
    else:
        # 2. Fallback to local file (for Local Development)
        cred = credentials.Certificate("serviceAccountKey.json")
        
    firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    import traceback
    print(f"CRITICAL: Firebase initialization failed: {str(e)}")
    traceback.print_exc() 
    print("Check if FIREBASE_CONFIG_JSON is valid JSON and contains all required fields.")
    db = None

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Firestore helper classes
class User(UserMixin):
    def __init__(self, id, username, email, password, is_admin=False):
        self.id = id
        self.username = username
        self.email = email
        self.password = password
        self.is_admin = is_admin

    @staticmethod
    def get_by_id(user_id):
        if not db: return None
        doc = db.collection('users').document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            return User(doc.id, **data)
        return None

    @staticmethod
    def get_by_username(username):
        if not db: return None
        users_ref = db.collection('users').where('username', '==', username).limit(1).stream()
        for user in users_ref:
            return User(user.id, **user.to_dict())
        return None

    @staticmethod
    def get_by_email(email):
        if not db: return None
        users_ref = db.collection('users').where('email', '==', email).limit(1).stream()
        for user in users_ref:
            return User(user.id, **user.to_dict())
        return None

class Prediction:
    def __init__(self, id, user_id, symptoms, predicted_disease, description, timestamp):
        self.id = id
        self.user_id = user_id
        self.symptoms = symptoms
        self.predicted_disease = predicted_disease
        self.description = description
        self.timestamp = timestamp

    @property
    def user(self):
        return User.get_by_id(self.user_id)

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

# Admin required decorator
from functools import wraps
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admins only!', 'danger')
            return redirect(url_for('landing'))
        return f(*args, **kwargs)
    return decorated_function

# Database setup handled by Firebase automatically

# load datasets ===========================================
try:
    sym_des = pd.read_csv("datasets/symtoms_df.csv")
    precautions = pd.read_csv("datasets/precautions_df.csv")
    workout = pd.read_csv("datasets/workout_df.csv")
    description = pd.read_csv("datasets/description.csv")
    medications = pd.read_csv('datasets/medications.csv')
    diets = pd.read_csv("datasets/diets.csv")
except Exception as e:
    print(f"Error loading datasets: {e}")

# load model ===========================================
svc = None
try:
    svc = pickle.load(open('models/svc.pkl','rb'))
except Exception as e:
    print(f"Error loading model: {e}")


# helper functions ===========================================
def helper(dis):
    desc = description[description['Disease'] == dis]['Description']
    desc = " ".join([w for w in desc])

    pre = precautions[precautions['Disease'] == dis][['Precaution_1', 'Precaution_2', 'Precaution_3', 'Precaution_4']]
    pre = [col for col in pre.values]

    med = medications[medications['Disease'] == dis]['Medication']
    med = [med for med in med.values]

    die = diets[diets['Disease'] == dis]['Diet']
    die = [die for die in die.values]

    wrkout = workout[workout['disease'] == dis]['workout']

    return desc, pre, med, die, wrkout

symptoms_dict = {'itching': 0, 'skin_rash': 1, 'nodal_skin_eruptions': 2, 'continuous_sneezing': 3, 'shivering': 4, 'chills': 5, 'joint_pain': 6, 'stomach_pain': 7, 'acidity': 8, 'ulcers_on_tongue': 9, 'muscle_wasting': 10, 'vomiting': 11, 'burning_micturition': 12, 'spotting_ urination': 13, 'fatigue': 14, 'weight_gain': 15, 'anxiety': 16, 'cold_hands_and_feets': 17, 'mood_swings': 18, 'weight_loss': 19, 'restlessness': 20, 'lethargy': 21, 'patches_in_throat': 22, 'irregular_sugar_level': 23, 'cough': 24, 'high_fever': 25, 'sunken_eyes': 26, 'breathlessness': 27, 'sweating': 28, 'dehydration': 29, 'indigestion': 30, 'headache': 31, 'yellowish_skin': 32, 'dark_urine': 33, 'nausea': 34, 'loss_of_appetite': 35, 'pain_behind_the_eyes': 36, 'back_pain': 37, 'constipation': 38, 'abdominal_pain': 39, 'diarrhoea': 40, 'mild_fever': 41, 'yellow_urine': 42, 'yellowing_of_eyes': 43, 'acute_liver_failure': 44, 'fluid_overload': 45, 'swelling_of_stomach': 46, 'swelled_lymph_nodes': 47, 'malaise': 48, 'blurred_and_distorted_vision': 49, 'phlegm': 50, 'throat_irritation': 51, 'redness_of_eyes': 52, 'sinus_pressure': 53, 'runny_nose': 54, 'congestion': 55, 'chest_pain': 56, 'weakness_in_limbs': 57, 'fast_heart_rate': 58, 'pain_during_bowel_movements': 59, 'pain_in_anal_region': 60, 'bloody_stool': 61, 'irritation_in_anus': 62, 'neck_pain': 63, 'dizziness': 64, 'cramps': 65, 'bruising': 66, 'obesity': 67, 'swollen_legs': 68, 'swollen_blood_vessels': 69, 'puffy_face_and_eyes': 70, 'enlarged_thyroid': 71, 'brittle_nails': 72, 'swollen_extremeties': 73, 'excessive_hunger': 74, 'extra_marital_contacts': 75, 'drying_and_tingling_lips': 76, 'slurred_speech': 77, 'knee_pain': 78, 'hip_joint_pain': 79, 'muscle_weakness': 80, 'stiff_neck': 81, 'swelling_joints': 82, 'movement_stiffness': 83, 'spinning_movements': 84, 'loss_of_balance': 85, 'unsteadiness': 86, 'weakness_of_one_body_side': 87, 'loss_of_smell': 88, 'bladder_discomfort': 89, 'foul_smell_of urine': 90, 'continuous_feel_of_urine': 91, 'passage_of_gases': 92, 'internal_itching': 93, 'toxic_look_(typhos)': 94, 'depression': 95, 'irritability': 96, 'muscle_pain': 97, 'altered_sensorium': 98, 'red_spots_over_body': 99, 'belly_pain': 100, 'abnormal_menstruation': 101, 'dischromic _patches': 102, 'watering_from_eyes': 103, 'increased_appetite': 104, 'polyuria': 105, 'family_history': 106, 'mucoid_sputum': 107, 'rusty_sputum': 108, 'lack_of_concentration': 109, 'visual_disturbances': 110, 'receiving_blood_transfusion': 111, 'receiving_unsterile_injections': 112, 'coma': 113, 'stomach_bleeding': 114, 'distention_of_abdomen': 115, 'history_of_alcohol_consumption': 116, 'fluid_overload.1': 117, 'blood_in_sputum': 118, 'prominent_veins_on_calf': 119, 'palpitations': 120, 'painful_walking': 121, 'pus_filled_pimples': 122, 'blackheads': 123, 'scurring': 124, 'skin_peeling': 125, 'silver_like_dusting': 126, 'small_dents_in_nails': 127, 'inflammatory_nails': 128, 'blister': 129, 'red_sore_around_nose': 130, 'yellow_crust_ooze': 131}
diseases_list = {15: 'Fungal infection', 4: 'Allergy', 16: 'GERD', 9: 'Chronic cholestasis', 14: 'Drug Reaction', 33: 'Peptic ulcer diseae', 1: 'AIDS', 12: 'Diabetes ', 17: 'Gastroenteritis', 6: 'Bronchial Asthma', 23: 'Hypertension ', 30: 'Migraine', 7: 'Cervical spondylosis', 32: 'Paralysis (brain hemorrhage)', 28: 'Jaundice', 29: 'Malaria', 8: 'Chicken pox', 11: 'Dengue', 37: 'Typhoid', 40: 'hepatitis A', 19: 'Hepatitis B', 20: 'Hepatitis C', 21: 'Hepatitis D', 22: 'Hepatitis E', 3: 'Alcoholic hepatitis', 36: 'Tuberculosis', 10: 'Common Cold', 34: 'Pneumonia', 13: 'Dimorphic hemmorhoids(piles)', 18: 'Heart attack', 39: 'Varicose veins', 26: 'Hypothyroidism', 24: 'Hyperthyroidism', 25: 'Hypoglycemia', 31: 'Osteoarthristis', 5: 'Arthritis', 0: '(vertigo) Paroymsal  Positional Vertigo', 2: 'Acne', 38: 'Urinary tract infection', 35: 'Psoriasis', 27: 'Impetigo'}

# Model Prediction function with Fuzzy Matching
def get_predicted_value(patient_symptoms):
    if svc is None:
        raise ValueError("Machine learning model (svc) is not loaded.")
    
    input_vector = np.zeros(len(symptoms_dict))
    matched_symptoms = []
    unrecognized_symptoms = []
    
    for item in patient_symptoms:
        # Fuzzy processing: lower case, replace space/dash with underscore
        clean_item = item.lower().replace(" ", "_").replace("-", "_").strip()
        
        if clean_item in symptoms_dict:
            input_vector[symptoms_dict[clean_item]] = 1
            matched_symptoms.append(clean_item)
        else:
            if clean_item: # Only track non-empty strings
                unrecognized_symptoms.append(item)
    
    # If no symptoms matched, we should inform the user
    # Dedup lists
    matched_symptoms = list(dict.fromkeys(matched_symptoms))
    unrecognized_symptoms = list(dict.fromkeys(unrecognized_symptoms))

    if not matched_symptoms:
        return None, [], unrecognized_symptoms

    prediction_idx = svc.predict([input_vector])[0]
    predicted_disease = diseases_list[prediction_idx]
    
    return predicted_disease, matched_symptoms, unrecognized_symptoms

# Routes ===========================================

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/predict-tool")
def index():
    symptoms = request.args.get('symptoms', '')
    return render_template("index.html", 
                           symptoms=symptoms, 
                           symptoms_list=list(symptoms_dict.keys()))

@app.route("/info")
def info():
    return render_template("info.html")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        admin_secret = request.form.get('admin_secret')

        if not db:
            flash('Database configuration error.', 'danger')
            return redirect(url_for('signup'))

        # Check existing user
        user_exists = User.get_by_username(username) or User.get_by_email(email)
        if user_exists:
            flash('Username or Email already exists!', 'danger')
            return redirect(url_for('signup'))

        is_admin = (admin_secret == "ADMIN123")
        user_data = {
            'username': username,
            'email': email,
            'password': password, # Storing plaintext as requested
            'is_admin': is_admin
        }
        # Use username as the document ID
        db.collection('users').document(username).set(user_data)
        flash('Registration successful!', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.get_by_username(username)

        # Checking plaintext password as requested
        if user and user.password == password:
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password!', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('landing'))

@app.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    if request.method == 'POST':
        symptoms = request.form.get('symptoms')
        if not symptoms or symptoms.strip() == "" or symptoms == "Symptoms":
            message = "Please enter your symptoms to get a diagnosis."
            return render_template('index.html', message=message, symptoms=symptoms)
        
        # Split by comma or semicolon
        import re
        user_symptoms = re.split(r'[,;]+', symptoms)
        user_symptoms = [s.strip() for s in user_symptoms if s.strip()]
        
        try:
            predicted_disease, matched, unrecognized = get_predicted_value(user_symptoms)
            
            if not predicted_disease:
                message = "The AI didn't recognize any of the symptoms entered. Please try using the suggestions or separate them with commas."
                return render_template('index.html', 
                                       message=message, 
                                       symptoms=symptoms,
                                       unrecognized=unrecognized,
                                       symptoms_list=list(symptoms_dict.keys()))

            dis_des, pre, med, die, workout_data = helper(predicted_disease)
            my_precautions = [i for i in pre[0]] if len(pre) > 0 else []

            # Save prediction to Firestore with a readable ID: username_timestamp
            timestamp = datetime.utcnow()
            prediction_data = {
                'user_id': current_user.id,
                'symptoms': symptoms,
                'predicted_disease': predicted_disease,
                'description': dis_des,
                'timestamp': timestamp
            }
            # Readable ID format: Username_YYYYMMDD_HHMMSS
            doc_id = f"{current_user.id}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            db.collection('predictions').document(doc_id).set(prediction_data)

            return render_template('result.html', 
                                   predicted_disease=predicted_disease, 
                                   dis_des=dis_des,
                                   my_precautions=my_precautions, 
                                   medications=med, 
                                   my_diet=die,
                                   workout=workout_data,
                                   symptoms=symptoms,
                                   matched_count=len(matched),
                                   matched_list=matched,
                                   unrecognized_list=unrecognized)
        except Exception as e:
            flash(f"Error during prediction: {str(e)}", "danger")
            return redirect(url_for('index', symptoms=symptoms))
    
    # GET request: also pass the full symbols list for datalist
    return render_template('index.html', symptoms_list=list(symptoms_dict.keys()))

@app.route('/history')
@login_required
def history():
    preds_ref = db.collection('predictions').where('user_id', '==', current_user.id).order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
    predictions = []
    for p in preds_ref:
        data = p.to_dict()
        predictions.append(Prediction(p.id, **data))
    return render_template('history.html', predictions=predictions)

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    users_ref = db.collection('users').stream()
    all_users = [User(u.id, **u.to_dict()) for u in users_ref]
    
    preds_ref = db.collection('predictions').order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
    all_predictions = []
    for p in preds_ref:
        data = p.to_dict()
        all_predictions.append(Prediction(p.id, **data))
        
    return render_template('admin.html', users=all_users, predictions=all_predictions)

@app.route('/admin/delete_prediction/<string:id>')
@login_required
@admin_required
def delete_prediction(id):
    db.collection('predictions').document(id).delete()
    flash('Prediction record deleted.', 'info')
    return redirect(url_for('admin_panel'))

@app.route('/export')
@login_required
def export():
    preds_ref = db.collection('predictions').where('user_id', '==', current_user.id).stream()
    user_predictions = []
    for p in preds_ref:
        user_predictions.append(p.to_dict())

    if not user_predictions:
        flash('No predictions to export!', 'warning')
        return redirect(url_for('history'))

    data = []
    for p in user_predictions:
        data.append({
            'Date': p['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if p.get('timestamp') else 'N/A',
            'Symptoms': p.get('symptoms', ''),
            'Predicted Disease': p.get('predicted_disease', ''),
            'Description': p.get('description', '')
        })

    df = pd.DataFrame(data)
    
    # Save to Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Predictions')
    output.seek(0)

    filename = f"predictions_{current_user.username}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/contact')
def contact():
    return render_template("contact.html")

@app.route('/developer')
def developer():
    return render_template("developer.html")

@app.route('/blog')
def blog():
    return render_template("blog.html")

if __name__ == '__main__':
    app.run(debug=True)