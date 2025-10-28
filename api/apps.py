# from django.apps import AppConfig


# class ApiConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'api'

#     def ready(self):
#         import api.signals

#         import firebase_admin
#         from firebase_admin import credentials

#         if not firebase_admin._apps:
#             cred = credentials.Certificate("NOTICE/firebase-adminsdk.json")
#             firebase_admin.initialize_app(cred)



from django.apps import AppConfig
import os
import firebase_admin
from firebase_admin import credentials

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        # Initialize Firebase if not already
        if not firebase_admin._apps:
            cred_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "NOTICE/firebase-adminsdk.json")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("Firebase Admin initialized")

        # Import signals after Firebase is ready
        import api.signals
