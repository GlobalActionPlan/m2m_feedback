# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from BTrees.OIBTree import OIBTree
from BTrees.OOBTree import OOBTree
from arche.api import Base
from arche.api import Content
from arche.interfaces import IObjectAddedEvent
from arche.interfaces import IObjectUpdatedEvent
from arche_m2m.interfaces import IChoice
from arche_m2m.interfaces import IQuestion
from arche_m2m.interfaces import IQuestionType
from arche_m2m.models.i18n import TranslationMixin
from pyramid.interfaces import IRequest
from pyramid.traversal import find_resource
from pyramid.traversal import find_root
from six import string_types
from zope.component import adapter
from zope.interface import implementer

from m2m_feedback import _
from m2m_feedback.interfaces import IFeedbackThreshold
from m2m_feedback.interfaces import IRuleSet
from m2m_feedback.interfaces import IScoreHandler
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
        q_cluster = _question_by_type_or_id(question)
        c_cluster = _choice_by_type_or_id(choice)
        assert isinstance(score, int)
        choices = self.choice_scores.setdefault(q_cluster, OIBTree())
        choices[c_cluster] = score

    def get_choice_score(self, question, choice, default = None):
        q_cluster = _question_by_type_or_id(question)
        c_cluster = _choice_by_type_or_id(choice)
        return self.choice_scores.get(q_cluster, {}).get(c_cluster, default)


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


@implementer(IScoreHandler)
@adapter(IRuleSet, IRequest)
class ScoreHandler(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def max_score(self, section, participant_uid):
        results = []
        for question in section.get_questions(self.request.locale_name, resolve = True):
            score = 0
            if not self.handle_question(section, question, participant_uid):
                continue
            for choice in get_all_choices(question, self.request, include_omitted = False):
                this_score = self.context.get_choice_score(question, choice)
                if this_score and this_score > score:
                    score = this_score
            results.append(score)
        return sum(results)

    def participant_score(self, section, participant_uid):
        scores = []
        for question in section.get_questions(self.request.locale_name, resolve = True):
            if not self.handle_question(section, question, participant_uid):
                continue
            choice = self.request.get_picked_choice(section, question, participant_uid)
            if choice:
                scores.append(self.context.get_choice_score(question, choice, default = 0))
        return sum(scores)

    def handle_question(self, section, question, participant_uid):
        question_widget = self.request.get_question_widget(question)
        if question_widget.allow_choices == True and question_widget.multichoice == False:
            choice_id = section.responses.get(participant_uid, {}).get(question.cluster)
            for choice in get_all_choices(question, self.request, include_omitted = True):
                if choice_id == choice.cluster and choice.omit_from_score_count == True:
                    return False
            return True
        return False

    def handle_choice(self, choice):
        return choice and getattr(choice, 'omit_from_score_count', False) == False

    def get_picked_choice_score(self, section, question, participant_uid):
        choice = self.request.get_picked_choice(section, question, participant_uid, default = None, lang = None)
        if self.handle_choice(choice):
            return self.context.get_choice_score(question, choice)

    def get_highest_choice_score(self, question):
        score = 0
        for choice in get_all_choices(question, self.request, include_omitted=False):
            this_score = self.context.get_choice_score(question, choice)
            if this_score and this_score > score:
                score = this_score
        return score


def get_all_choices(question, request, only_from_type = False, locale_name = None, include_omitted = False):
    """
    :return: Choice objects
    :rtype: List
    """
    if locale_name == None:
        locale_name = request.locale_name
    question_type = None
    if IQuestion.providedBy(question):
        question_type = request.get_question_type(question)
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

def _choice_by_type_or_id(obj):
    if IChoice.providedBy(obj):
        return obj.cluster
    #Assume cluster id as argument
    if obj and isinstance(obj, string_types):
        return obj
    raise TypeError("%r was not a Choice instance or a cluster id of a question" % obj)

def _question_by_type_or_id(obj):
    if IQuestion.providedBy(obj):
        return obj.cluster
    #Assume cluster id as argument
    if obj and isinstance(obj, string_types):
        return obj
    raise TypeError("%r was not a Question instance or a cluster id of a question" % obj)

def includeme(config):
    config.add_content_factory(RuleSet, addable_to = ('Organisation', 'Root'))
    config.add_content_factory(SurveyFeedback, addable_to = 'Survey')
    config.add_content_factory(FeedbackThreshold, addable_to = 'SurveyFeedback')
    config.registry.registerAdapter(ScoreHandler)
    config.add_subscriber(update_siblings_score_count, [IChoice, IObjectAddedEvent])
    config.add_subscriber(update_siblings_score_count, [IChoice, IObjectUpdatedEvent])
    from arche_m2m.models.question_type import Choice
    Choice.omit_from_score_count = False
