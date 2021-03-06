from django.shortcuts import render
from django.conf import settings
from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404, redirect

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
# from django.forms.models import inlineformset_factory

from survey.models import Commutersurvey, Employer, Leg, Month
from survey.forms import CommuterForm, ExtraCommuterForm
from survey.forms import MakeLegs_NormalTW, MakeLegs_NormalFW, MakeLegs_WRTW, MakeLegs_WRFW

import json
import mandrill
from datetime import date


from django.core.mail import send_mail, BadHeaderError
from django.http import HttpResponse, HttpResponseRedirect


def add_checkin(request):

    try:
        wr_day = Month.objects.get(open_checkin__lte=date.today(),
                                   close_checkin__gte=date.today())
    except Month.DoesNotExist:
        return redirect('/')



    if request.method == 'POST':
        # send the filled out forms in!
        # if the forms turn out to be not valid, they will still retain
        # the form data from the POST request this way.

        commute_form = CommuterForm(request.POST)
        extra_commute_form = ExtraCommuterForm(request.POST)
        leg_formset_NormalTW = MakeLegs_NormalTW(request.POST, instance=Commutersurvey(),
                                                 prefix='ntw')
        leg_formset_NormalFW = MakeLegs_NormalFW(request.POST, instance=Commutersurvey(),
                                                 prefix='nfw')
        leg_formset_WRTW = MakeLegs_WRTW(request.POST, instance=Commutersurvey(), prefix='wtw')
        leg_formset_WRFW = MakeLegs_WRFW(request.POST, instance=Commutersurvey(), prefix='wfw')

        # if the main form is correct
        if commute_form.is_valid():
            commutersurvey = commute_form.save(commit=False)
            commutersurvey.wr_day_month = wr_day
            commutersurvey.email = commute_form.cleaned_data['email']
            commutersurvey.employer = commute_form.cleaned_data['employer']
            if 'team' in commute_form.cleaned_data:
                commutersurvey.team = commute_form.cleaned_data['team']

            # write form responses to cookie
            for attr in ['name', 'email', 'home_address', 'work_address']:
                # TODO: include employer and team
                if attr in commute_form.cleaned_data:
                    request.session[attr] = commute_form.cleaned_data[attr]

            extra_commute_form.is_valid() # creates cleaned_data
            if 'share' in extra_commute_form.cleaned_data:
                commutersurvey.share = extra_commute_form.cleaned_data['share']
            commutersurvey.comments = extra_commute_form.cleaned_data['comments']

            # write form responses to cookie
            for attr in ['share', 'comments', 'volunteer']:
                if attr in extra_commute_form.cleaned_data:
                    request.session[attr] = extra_commute_form.cleaned_data[attr]

            leg_formset_NormalTW = MakeLegs_NormalTW(request.POST, instance=commutersurvey, prefix='ntw')
            leg_formset_NormalFW = MakeLegs_NormalFW(request.POST, instance=commutersurvey, prefix='nfw')
            leg_formset_WRTW = MakeLegs_WRTW(request.POST, instance=commutersurvey, prefix='wtw')
            leg_formset_WRFW = MakeLegs_WRFW(request.POST, instance=commutersurvey, prefix='wfw')

            # finally! we're good to go.
            if (leg_formset_WRTW.is_valid() and
                leg_formset_NormalTW.is_valid() and
                leg_formset_NormalFW.is_valid() and
                leg_formset_WRFW.is_valid()):

                commutersurvey.save()
                leg_formset_WRTW.save()
                leg_formset_WRFW.save()
                leg_formset_NormalTW.save()
                leg_formset_NormalFW.save()
                # very simple email sending - replace using Mandrill API later
                name = commutersurvey.name or 'Supporter'
                subject = ('Walk/Ride Day ' +
                           commutersurvey.wr_day_month.month + ' Checkin')
                message_html = (
                    '<p>Dear {name},</p><p>Thank you for checking'
                    ' in your Walk/Ride Day commute! This email confirms your'
                    ' participation in {survey_date}\'s Walk/Ride Day! Feel '
                    'free to show it to our <a href="http://checkin'
                    '-greenstreets.rhcloud.com/retail" style="color:'
                    '#2ba6cb;text-decoration: none;">Retail Partners</a> '
                    'to take advantage of their offers of freebies, '
                    'discounts, and other goodies!</p><p>If you haven\'t already, <a href="http://'
                    'checkin2015-greenstreets.rhcloud.com/leaderboard/" '
                    'style="color: #2ba6cb;text-decoration: none;">CLICK HERE'
                    '</a> to see how your company did in the 2015 Corporate'
                    ' Challenge, which ended with the October Walk/Ride Day.</p>'
                    '<p>Thank you for being involved! Remember to check-in '
                    'for next month\'s Walk/Ride Day.</p><p>Warmly,<br>'
                    '<span style="color:#006600;font-weight:bold;">Janie Katz'
                    '-Christy, Director <br>Green Streets Initiative<br> '
                    '<span class="mobile_link">617-299-1872 (office)</p>'
                    '<p>Share with your friends and colleagues! '
                    '<a href="http://checkin.gogreenstreets.org" '
                    'style="color: #2ba6cb;text-decoration: none;">Make sure'
                    ' they get a chance to check in</p>'.format(
                        name=name,
                        survey_date=commutersurvey.wr_day_month.month))

                message_plain = (
                    'Dear Supporter, Thank you for checking in '
                    'your Walk/Ride Day commute! This email confirms your'
                    ' participation in ' + commutersurvey.wr_day_month.month +
                    '\'s Walk/Ride Day! Feel free to show it to our Retail'
                    ' Partners to take advantage of their offers of freebies,'
                    ' discounts, and other goodies! Thank you for being'
                    ' involved! Remember to check-in for next month\'s Walk/Ride'
                    ' Day. Warmly, Green Streets Initiative')
                recipient_list = [commutersurvey.email,]
                from_email = 'checkin@gogreenstreets.org'
                send_mail(subject, message_plain, from_email, recipient_list,
                          html_message=message_html, fail_silently=True)
                return render_to_response(
                        'survey/thanks.html',
                        {
                            'person': commutersurvey.name,
                            'calories_burned': commutersurvey.calories_total,
                            'calorie_change': commutersurvey.calorie_change,
                            'carbon_savings': commutersurvey.carbon_savings,
                            'change_type': commutersurvey.change_type
                        })

    else:
        # initialize forms with cookies
        initial_commute = {}
        initial_extra_commute = {}

        for attr in ['name', 'email', 'home_address', 'work_address']:
            if attr in request.session:
                initial_commute[attr] = request.session.get(attr)

        for attr in ['share', 'comments', 'volunteer']:
            if attr in request.session:
                initial_extra_commute[attr] = request.session.get(attr)

        commute_form = CommuterForm(initial=initial_commute)
        extra_commute_form = ExtraCommuterForm(initial=initial_extra_commute)

        # TODO: use request session to instantiate the formsets with initial=[{},{},{}...] for each formset

        leg_formset_NormalTW = MakeLegs_NormalTW(instance=Commutersurvey(), prefix='ntw')
        leg_formset_NormalFW = MakeLegs_NormalFW(instance=Commutersurvey(), prefix='nfw')
        leg_formset_WRTW = MakeLegs_WRTW(instance=Commutersurvey(), prefix='wtw')
        leg_formset_WRFW = MakeLegs_WRFW(instance=Commutersurvey(), prefix='wfw')

    return render(request, "survey/new_checkin.html",
                  {
                      'wr_day': wr_day,
                      'form': commute_form,
                      'extra_form': extra_commute_form,
                      'NormalTW_formset': leg_formset_NormalTW,
                      'NormalFW_formset': leg_formset_NormalFW,
                      'WRTW_formset': leg_formset_WRTW,
                      'WRFW_formset': leg_formset_WRFW
                  })
