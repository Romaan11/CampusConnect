from django.contrib import admin
from api.models import Notice, Routine, DeviceToken, Profile, AdmissionRecord, Event

admin.site.register(Notice)
admin.site.register(Routine)
admin.site.register(DeviceToken)
admin.site.register(Profile)
admin.site.register(Event)
admin.site.register(AdmissionRecord)


# @admin.register(AdmissionRecord)
# class AdmissionRecordAdmin(admin.ModelAdmin):
#     list_display = ('first_name', 'last_name', 'email', 'roll_no', 'semester')
#     readonly_fields = ('image_preview',)

#     def image_preview(self, obj):
#         if obj.image:
#             return mark_safe(f'<img src="{obj.image.url}" width="100" />')
#         return "-"
#     image_preview.short_description = "Image"