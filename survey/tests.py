from django.test import TestCase
from survey.forms import LegForm1, MakeLegs_NormalFW
from survey.forms import Commutersurvey, Leg
import models


class ModeTests(TestCase):

    def setUp(self):
        models.Mode.objects.create(name="bike", met=50.0,
                                   carb=0.0, speed=20.0, green=True)

    def test_create_mode(self):
        bike = models.Mode.objects.get(name='bike')
        self.assertEqual(bike.name, 'bike')
        self.assertEqual(bike.speed, 20.0)
        self.assertEqual(bike.carb, 0.0)
        self.assertEqual(bike.met, 50.0)
        self.assertEqual(bike.green, True)


class LegFormTests(TestCase):

    def setUp(self):
        pass

    def test_empty_form_leg_1(self):
        form = LegForm1(data={})
        self.assertFalse(form.is_valid())

    # def test_empty_MakeLegs_NormalFW(self):
    #     hi = MakeLegs_NormalFW(instance=Commutersurvey(), prefix='nfw')
    #     hi.is_valid()
    #
