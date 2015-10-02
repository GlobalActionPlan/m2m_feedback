# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from BTrees.OIBTree import OIBTree
from BTrees.OOBTree import OOBTree
from arche.api import Content
from arche_m2m.interfaces import IChoice
from arche_m2m.interfaces import IQuestion
from zope.interface import implementer

from m2m_feedback import _
from m2m_feedback.interfaces import IRuleSet


@implementer(IRuleSet)
class RuleSet(Content):
    type_title = _("Ruleset")
    type_name = "RuleSet"
    add_permission = "Add %s" % type_name
    _referenced_questions = frozenset()
    choice_scores = None

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


def includeme(config):
    config.add_content_factory(RuleSet, addable_to = ('Organisation', 'Root'))
