# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from BTrees.OIBTree import OIBTree
from BTrees.OOBTree import OOBTree
from arche.api import Content
from arche_m2m.interfaces import IChoice
from arche_m2m.interfaces import IQuestion
from arche_m2m.models.i18n import TranslationMixin
from zope.interface import implementer

from m2m_feedback import _
from m2m_feedback.interfaces import IRuleSet
from m2m_feedback.interfaces import ISurveyFeedback


@implementer(IRuleSet)
class RuleSet(Content):
    type_title = _("Ruleset")
    _referenced_questions = frozenset()
    choice_scores = None
    nav_visible = False

    @property
    def referenced_questions(self):
        return self._referenced_questions
    @referenced_questions.setter
    def referenced_questions(self, value):
        self._referenced_questions = frozenset(value)

    def __init__(self, **kw):
        super(RuleSet, self).__init__(**kw)
        self.choice_scores = OOBTree()

    def set_choice_score(self, question, choice, score):
        assert IQuestion.providedBy(question)
        assert IChoice.providedBy(choice)
        assert isinstance(score, int)
        choices = self.choice_scores.setdefault(question.cluster, OIBTree())
        choices[choice.cluster] = score

    def get_choice_score(self, question, choice, default = None):
        return self.choice_scores.get(question.cluster, {}).get(choice.cluster, default)


@implementer(ISurveyFeedback)
class SurveyFeedback(Content, TranslationMixin):
    type_title = _("Survey Feedback")
    ruleset = ''
    default_view = 'dynamic_view'
    _referenced_sections = frozenset()

    @property
    def referenced_sections(self):
        return self._referenced_sections
    @referenced_sections.setter
    def referenced_sections(self, value):
        self._referenced_sections = frozenset(value)


def includeme(config):
    config.add_content_factory(RuleSet, addable_to = ('Organisation', 'Root'))
    config.add_content_factory(SurveyFeedback, addable_to = 'Survey')
