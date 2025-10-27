from django.contrib import admin
from api.models import Notice, Routine, DeviceToken, Profile, AdmissionRecord, Event

admin.site.register(Notice)
admin.site.register(Routine)
admin.site.register(DeviceToken)
admin.site.register(Profile)
admin.site.register(AdmissionRecord)
admin.site.register(Event)
