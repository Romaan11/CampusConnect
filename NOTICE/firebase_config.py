# NOTICE/firebase_config.py
import firebase_admin
from firebase_admin import credentials, messaging

cred = credentials.Certificate("NOTICE/firebase-adminsdk.json")
firebase_admin.initialize_app(cred)
