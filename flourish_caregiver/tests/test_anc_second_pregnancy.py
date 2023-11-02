from dateutil.relativedelta import relativedelta
from django.test import tag, TestCase
from edc_base import get_utcnow
from edc_facility.import_holidays import import_holidays
from model_mommy import mommy

from flourish_caregiver.models import (OnScheduleCohortAAntenatal,
                                       OnScheduleCohortABirth,
                                       SubjectConsent)
from flourish_caregiver.subject_helper_mixin import SubjectHelperMixin


@tag('tasp')
class TestANCSecondPregnancy(TestCase):

    def setUp(self):
        import_holidays()
        self.subject_helper = SubjectHelperMixin()

        self.subject_identifier = self.subject_helper.create_antenatal_enrollment()

        self.caregiver_onschedule = OnScheduleCohortAAntenatal.objects.get(
            subject_identifier=self.subject_identifier, )

        mommy.make_recipe(
            'flourish_caregiver.maternaldelivery',
            subject_identifier=self.subject_identifier,
            child_subject_identifier=self.caregiver_onschedule.child_subject_identifier,
            delivery_datetime=get_utcnow() - relativedelta(days=1),
        )

        mommy.make_recipe(
            'flourish_child.childbirth',
            subject_identifier=self.caregiver_onschedule.child_subject_identifier,
            dob=(get_utcnow() - relativedelta(days=1)).date(),
            user_created='imosweu')

        self.subject_consent = SubjectConsent.objects.get(
            subject_identifier=self.subject_identifier
        )

    def test_anc_second_pregnancy_enrollment(self):
        self.assertEqual(OnScheduleCohortAAntenatal.objects.filter(
            subject_identifier=self.subject_identifier,
            schedule_name='a_antenatal1_schedule1').count(), 1)

        child_2 = mommy.make_recipe(
            'flourish_caregiver.caregiverchildconsent',
            subject_consent=self.subject_consent,
            child_dob=None,
            first_name=None,
            last_name=None, )

        mommy.make_recipe(
            'flourish_caregiver.antenatalenrollment',
            subject_identifier=self.subject_identifier,
            child_subject_identifier=child_2.subject_identifier,
        )

        self.assertNotEqual(child_2.subject_identifier,
                            self.caregiver_onschedule.child_subject_identifier)

        self.assertEqual(OnScheduleCohortAAntenatal.objects.filter(
            subject_identifier=self.subject_identifier,
            schedule_name='a_antenatal2_schedule1').count(), 1)

        self.assertEqual(OnScheduleCohortAAntenatal.objects.filter(
            subject_identifier=self.subject_identifier).count(), 2)

        self.assertEqual(OnScheduleCohortAAntenatal.objects.filter(
            subject_identifier=self.subject_identifier,
            child_subject_identifier=child_2.subject_identifier).count(), 1)

    def test_anc_second_pregnancy_birth(self):
        self.assertEqual(OnScheduleCohortABirth.objects.filter(
            subject_identifier=self.subject_identifier,
            schedule_name='a_birth1_schedule1').count(), 1)

        child_2 = mommy.make_recipe(
            'flourish_caregiver.caregiverchildconsent',
            subject_consent=self.subject_consent,
            child_dob=None,
            first_name=None,
            last_name=None, )

        mommy.make_recipe(
            'flourish_caregiver.antenatalenrollment',
            subject_identifier=self.subject_identifier,
            child_subject_identifier=child_2.subject_identifier,
        )

        mommy.make_recipe(
            'flourish_caregiver.maternaldelivery',
            subject_identifier=self.subject_identifier,
            child_subject_identifier=child_2.subject_identifier,
            delivery_datetime=get_utcnow(),
        )

        mommy.make_recipe(
            'flourish_child.childbirth',
            subject_identifier=child_2.subject_identifier,
            dob=get_utcnow().date(),
            user_created='imosweu')

        self.assertEqual(OnScheduleCohortABirth.objects.filter(
            subject_identifier=self.subject_identifier,
            schedule_name='a_birth2_schedule1').count(), 1)
