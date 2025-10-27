# api/utils.py
from firebase_admin import messaging

def send_fcm_notification(token, title, body, data=None):
    """
    Send a Firebase Cloud Messaging (FCM) notification to a device.
    - token: the FCM device token (string)
    - title: notification title (string)
    - body: notification body (string)
    - data: optional dictionary of extra key-value pairs
    """
    if not token:
        return None

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        token=token,
        data=data or {}
    )

    try:
        response = messaging.send(message)
        print("Successfully sent message:", response)
        return response
    except Exception as e:
        print("Error sending FCM message:", e)
        return None
