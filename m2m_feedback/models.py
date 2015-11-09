# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from BTrees.OIBTree import OIBTree
from BTrees.OOBTree import OOBTree
from arche.api import Base
from arche.api import Content
from arche.interfaces import IObjectAddedEvent
from arche.interfaces import IObjectUpdatedEvent
from arche.utils import resolve_docids
from arche_m2m.interfaces import IChoice
from arche_m2m.interfaces import IQuestion
from arche_m2m.interfaces import IQuestionType
from arche_m2m.models.i18n import TranslationMixin
from pyramid.traversal import find_resource
from pyramid.traversal import find_root
from zope.interface import implementer

from m2m_feedback import _
from m2m_feedback.interfaces import IFeedbackThreshold
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
        if IQuestion.providedBy(question):
            question = question.cluster
        if IChoice.providedBy(choice):
            choice = choice.cluster
        return self.choice_scores.get(question, {}).get(choice, default)


@implementer(ISurveyFeedback)
class SurveyFeedback(Content, TranslationMixin):
    type_title = _("Survey Feedback")
    ruleset = ''
    section = ''


@implementer(IFeedbackThreshold)
class FeedbackThreshold(Base):
    type_title = _("Feedback threshold")
    default_view = 'dynamic_view'
    percentage = 0
    title = ""
    description = ""
    colour = ""

    def __repr__(self):
        klass = self.__class__
        classname = '%s.%s' % (klass.__module__, klass.__name__)
        return '<%s object %r at %#x>' % (classname,
                                          self.__name__,
                                          id(self))

def get_all_choices(question, request, only_from_type = False, locale_name = None, include_omitted = False):
    if locale_name == None:
        locale_name = request.locale_name
    question_type = None
    if IQuestion.providedBy(question):
        docids = request.root.catalog.query("uid == '%s'" % question.question_type)[1]
        #Generator
        for qt in resolve_docids(request, docids, perm = None):
            question_type = qt
    elif IQuestionType.providedBy(question):
        question_type = question
        question = None
    else:
        raise TypeError("question must be either a QuestionType or Question object.")
    #Get from type
    choices = list(question_type.get_choices(locale_name))
    if question and only_from_type == False:
        choices.extend(question.get_choices(locale_name))
    if include_omitted == False:
        choices = [x for x in choices if x.omit_from_score_count == False]
    return choices

def get_relevant_threshold(context, score):
    if not ISurveyFeedback.providedBy(context):
        raise TypeError("context must be a SurveyFeedback object")
    thresholds = [x for x in context.values() if IFeedbackThreshold.providedBy(x)]
    for obj in sorted(thresholds, key = lambda x: x.percentage, reverse = True):
        if obj.percentage <= score:
            return obj

def update_siblings_score_count(context, event):
    root = find_root(context)
    query = "cluster == '%s' " % context.cluster
    query += "and uid != '%s'" % context.uid
    for docid in root.catalog.query(query)[1]:
        path = root.document_map.address_for_docid(docid)
        obj = find_resource(root, path)
        if context.omit_from_score_count != obj.omit_from_score_count:
            obj.omit_from_score_count = context.omit_from_score_count

def includeme(config):
    config.add_content_factory(RuleSet, addable_to = ('Organisation', 'Root'))
    config.add_content_factory(SurveyFeedback, addable_to = 'Survey')
    config.add_content_factory(FeedbackThreshold, addable_to = 'SurveyFeedback')
    config.add_subscriber(update_siblings_score_count, [IChoice, IObjectAddedEvent])
    config.add_subscriber(update_siblings_score_count, [IChoice, IObjectUpdatedEvent])
    from arche_m2m.models.question_type import Choice
    Choice.omit_from_score_count = False
