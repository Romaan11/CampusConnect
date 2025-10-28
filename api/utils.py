# # # api/utils.py
# # from firebase_admin import messaging

# # def send_fcm_notification(token, title, body, data=None):
# #     """
# #     Send a Firebase Cloud Messaging (FCM) notification to a device.
# #     - token: the FCM device token (string)
# #     - title: notification title (string)
# #     - body: notification body (string)
# #     - data: optional dictionary of extra key-value pairs
# #     """
# #     if not token:
# #         return None

# #     message = messaging.Message(
# #         notification=messaging.Notification(
# #             title=title,
# #             body=body
# #         ),
# #         token=token,
# #         data=data or {}
# #     )

# #     try:
# #         response = messaging.send(message)
# #         print("Successfully sent message:", response)
# #         return response
# #     except Exception as e:
# #         print("Error sending FCM message:", e)
# #         return None






# # api/utils.py
# from firebase_admin import messaging
# from .models import DeviceToken

# def send_fcm_notification(token, title, body, data=None):
#     """Send to a single device token."""
#     if not token:
#         return None
#     message = messaging.Message(
#         notification=messaging.Notification(title=title, body=body),
#         token=token,
#         data=data or {}
#     )
#     try:
#         response = messaging.send(message)
#         print("Successfully sent message:", response)
#         return response
#     except Exception as e:
#         print("Error sending FCM message:", e)
#         return None


# def send_fcm_to_all(title, body, data=None):
#     """Send the same message to all registered devices."""
#     tokens = list(DeviceToken.objects.values_list("token", flat=True))
#     if not tokens:
#         print("No device tokens found.")
#         return

#     message = messaging.MulticastMessage(
#         notification=messaging.Notification(title=title, body=body),
#         data=data or {},
#         tokens=tokens
#     )

#     try:
#         response = messaging.send_multicast(message)
#         print(f"Sent to {len(tokens)} devices; {response.success_count} succeeded, {response.failure_count} failed.")
#         return response
#     except Exception as e:
#         print("Error sending multicast FCM:", e)
#         return None



# api/utils.py
from firebase_admin import messaging
from .models import DeviceToken

def send_fcm_notification(token, title, body, data=None):
    """Send to a single device token."""
    if not token:
        return None
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
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

def send_fcm_to_all(title, body, data=None):
    """Send the same message to all registered devices (compatible with firebase-admin 7.1.0)."""
    tokens = list(DeviceToken.objects.values_list("token", flat=True))
    if not tokens:
        print("No device tokens found.")
        return

    success_count = 0
    failure_count = 0

    for token in tokens:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=token,
            data=data or {}
        )
        try:
            messaging.send(message)
            success_count += 1
        except Exception as e:
            print(f"Error sending FCM to {token}: {e}")
            failure_count += 1

    print(f"Sent to {len(tokens)} devices; {success_count} succeeded, {failure_count} failed.")
    return {"success_count": success_count, "failure_count": failure_count}

