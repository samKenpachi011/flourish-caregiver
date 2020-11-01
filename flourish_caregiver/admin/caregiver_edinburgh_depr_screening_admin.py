from django.contrib import admin
from edc_model_admin import audit_fieldset_tuple

from .modeladmin_mixins import CrfModelAdminMixin
from ..admin_site import flourish_maternal_admin
from ..forms import CaregiverEdinburghDeprScreeningForm
from ..models import CaregiverEdinburghDeprScreening


@admin.register(CaregiverEdinburghDeprScreening, site=flourish_maternal_admin)
class CaregiverEdinburghDeprScreeningAdmin(CrfModelAdminMixin, admin.ModelAdmin):

    form = CaregiverEdinburghDeprScreeningForm

    fieldsets = (
        (None, {
            'fields': [
                'maternal_visit',
                'report_datetime',
                'able_to_laugh',
                'enjoyment_to_things',
                'self_blame',
                'anxious',
                'panicky',
                'coping',
                'sleeping_difficulty',
                'miserable_feeling',
                'unhappy',
                'self_harm',
            ]}
         ), audit_fieldset_tuple)

    radio_fields = {'able_to_laugh': admin.VERTICAL,
                    'enjoyment_to_things': admin.VERTICAL,
                    'self_blame': admin.VERTICAL,
                    'anxious': admin.VERTICAL,
                    'panicky': admin.VERTICAL,
                    'coping': admin.VERTICAL,
                    'sleeping_difficulty': admin.VERTICAL,
                    'miserable_feeling': admin.VERTICAL,
                    'unhappy': admin.VERTICAL,
                    'self_harm': admin.VERTICAL,}