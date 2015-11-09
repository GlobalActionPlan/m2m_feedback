from __future__ import absolute_import

from arche.fanstatic_lib import main_css
from fanstatic import Library
from fanstatic import Resource
from arche.interfaces import IViewInitializedEvent


lib_m2m_feedback = Library("m2m_feedback", "static")
m2m_feedback_css = Resource(lib_m2m_feedback, 'main.css', depends = (main_css,))

def need_feedback_css(view, event):
    m2m_feedback_css.need()

def includeme(config):
    from m2m_feedback.views import SurveyFeedbackForm
    config.add_subscriber(need_feedback_css, [SurveyFeedbackForm, IViewInitializedEvent])
