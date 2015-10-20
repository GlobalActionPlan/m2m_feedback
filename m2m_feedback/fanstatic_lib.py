from __future__ import absolute_import

from arche.fanstatic_lib import main_css
from fanstatic import Library
from fanstatic import Resource


lib_m2m_feedback = Library("m2m_feedback", "static")

m2m_feedback_main_css = Resource(lib_m2m_feedback, 'main.css', depends = (main_css,))
