from dateutil.relativedelta import relativedelta
from django.apps import apps as django_apps
from django.db.models import Q
from edc_appointment.models import Appointment
from edc_appointment.constants import NEW_APPT
from edc_base import get_utcnow
from edc_visit_schedule import site_visit_schedules
from flourish_caregiver.helper_classes.schedule_dict import child_schedule_dict, \
    caregiver_schedule_dict


class SeqEnrolOnScheduleMixin:
    child_appointment_model = 'flourish_child.appointment'

    @property
    def child_appointment_cls(self):
        return django_apps.get_model(self.child_appointment_model)

    def put_caregiver_onschedule(self):
        """Put a caregiver on schedule.
        """
        cohort = self.evaluated_cohort
        schedule_type = self.schedule_type
        child_count = str(self.child_consent_obj.caregiver_visit_count)
        onschedule_datetime = self.caregiver_last_qt_subject_schedule_obj.onschedule_datetime

        # TODO: To get variables needed from the model
        onschedule_model = caregiver_schedule_dict[cohort][schedule_type][
            'onschedule_model']
        schedule_name = caregiver_schedule_dict[cohort][schedule_type][child_count]

        self.put_on_schedule(onschedule_model=onschedule_model,
                                schedule_name=schedule_name,
                                onschedule_datetime=onschedule_datetime,
                                subject_identifier=self.caregiver_subject_identifier,
                                is_caregiver=True)

        self.delete_completed_appointments(
            appointment_model_cls=Appointment,
            subject_identifier=self.caregiver_subject_identifier,
            schedule_name=schedule_name)

        if '_sec' not in cohort:
            fu_onschedule_model =  caregiver_schedule_dict[cohort]['sq_followup']['onschedule_model']
            fu_schedule_name =  caregiver_schedule_dict[cohort]['sq_followup'][child_count]

            self.enrol_fu_schedule(
                cohort=cohort,
                subject_identifier=self.caregiver_subject_identifier,
                schedule_name=fu_schedule_name,
                onschedule_model=fu_onschedule_model,
                is_caregiver=True)

    def put_child_onschedule(self):

        cohort = self.evaluated_cohort
        schedule_type = self.schedule_type

        onschedule_model = child_schedule_dict[cohort][schedule_type]['onschedule_model']
        schedule_name = child_schedule_dict[cohort][schedule_type]['name']
        onschedule_datetime = self.child_last_qt_subject_schedule_obj.onschedule_datetime

        _, schedule = site_visit_schedules.get_by_onschedule_model_schedule_name(
            onschedule_model=onschedule_model,
            name=schedule_name)

        if not schedule.is_onschedule(subject_identifier=self.child_subject_identifier,
                                      report_datetime=onschedule_datetime):
            self.put_on_schedule(onschedule_model=onschedule_model,
                                 schedule_name=schedule_name,
                                 base_appt_datetime=onschedule_datetime,
                                 subject_identifier=self.child_subject_identifier)

            self.delete_completed_appointments(
                appointment_model_cls=self.child_appointment_cls,
                subject_identifier=self.child_subject_identifier,
                schedule_name=schedule_name)

        if '_sec' not in cohort:
            fu_onschedule_model = child_schedule_dict[cohort]['sq_followup']['onschedule_model']
            fu_schedule_name = child_schedule_dict[cohort]['sq_followup']['name']
        
            self.enrol_fu_schedule(cohort=cohort,
                                   subject_identifier=self.child_subject_identifier,
                                   schedule_name=fu_schedule_name,
                                   onschedule_model=fu_onschedule_model, )

    def put_on_schedule(self, onschedule_model, schedule_name,
                        subject_identifier, base_appt_datetime=None, is_caregiver=False, 
                        onschedule_datetime = get_utcnow()):
        
        

        _, schedule = site_visit_schedules.get_by_onschedule_model_schedule_name(
            onschedule_model=onschedule_model,
            name=schedule_name)
        schedule.put_on_schedule(
            subject_identifier=subject_identifier,
            onschedule_datetime=onschedule_datetime,
            base_appt_datetime=base_appt_datetime,
            schedule_name=schedule_name)

        if is_caregiver:
            self.update_onschedule_model(onschedule_model=onschedule_model,
                                         schedule_name=schedule_name, schedule=schedule)
            
    def update_onschedule_model(self, onschedule_model, schedule_name, schedule):

        onschedule_model_cls = django_apps.get_model(onschedule_model)
        try:
            onschedule_model_cls.objects.get(
                subject_identifier=self.caregiver_subject_identifier,
                schedule_name=schedule_name,
                child_subject_identifier=self.child_subject_identifier)
        except onschedule_model_cls.DoesNotExist:
            try:
                onschedule_obj = schedule.onschedule_model_cls.objects.get(
                    subject_identifier=self.caregiver_subject_identifier,
                    schedule_name=schedule_name)
            except schedule.onschedule_model_cls.DoesNotExist:
                pass
            else:
                onschedule_obj.child_subject_identifier = self.child_subject_identifier
                onschedule_obj.save()

    @classmethod
    def delete_completed_appointments(cls, appointment_model_cls, subject_identifier,
                                      schedule_name ):
        """Deletes completed appointments from previous schedules which are present in
        new schedules.

        Args:
            appointment_model_cls (Type[Appointment]): Model class for Appointments.
            subject_identifier (str): Unique identifier for the subject.
            schedule_name (str): New schedule participant is enrolled on.
        Returns:
            None
        """
        complete_appts = appointment_model_cls.objects.filter(
            Q(schedule_name__icontains='quart') | Q(schedule_name__icontains='qt'),
            subject_identifier=subject_identifier, ).exclude(
                appt_status=NEW_APPT).values_list('visit_code', flat=True).distinct()
        
        new_appts = appointment_model_cls.objects.filter(
            subject_identifier=subject_identifier,
            schedule_name=schedule_name,
            visit_code__in=complete_appts)
        if new_appts.exists():
            new_appts.delete()

    def enrol_fu_schedule(self, cohort, subject_identifier, schedule_name, onschedule_model,
                          is_caregiver=False, ):
        """ Put participant on FU schedule for sequential cohort, based on age criteria:
            Cohort A → B: Follow-up visit occurs at 7 years, if already 7 years occurs 6
            months after.
            Cohort B → C: Follow-up visit occurs at 12 years, if already 12 years occurs
            6 months after.
            @param cohort: sequentially enrolled cohort
            @param subject_identifier: participant sid
            @param schedule_name: schedule name for sequentially enrolled cohort
            @param onschedule_model: onschedule model name for sequentially enrolled cohort
            @param is_caregiver: bool representing caregiver/child participant   
        """
        cohort_ages = {'cohort_b': 7, 'cohort_c': 12}
        onschedule_datetime = None
        closeout_dt = django_apps.get_app_config('edc_protocol').study_close_datetime
        age_fu = cohort_ages.get(cohort, self.child_current_age)
        if self.child_current_age < age_fu:
            age_diff = round(age_fu - self.child_current_age, 2)
            age_in_months = round(age_diff * 12)
            onschedule_datetime = get_utcnow() + relativedelta(months=age_in_months)
        else:
            onschedule_datetime = get_utcnow() + relativedelta(months=6)

        if onschedule_datetime:
            onschedule_datetime = (closeout_dt if onschedule_datetime > closeout_dt
                                   else onschedule_datetime)
            self.put_on_schedule(onschedule_model=onschedule_model,
                                 schedule_name=schedule_name,
                                 base_appt_datetime=onschedule_datetime,
                                 subject_identifier=subject_identifier,
                                 is_caregiver=is_caregiver)
