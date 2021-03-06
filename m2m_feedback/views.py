# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from decimal import Decimal
from decimal import InvalidOperation

from arche.security import NO_PERMISSION_REQUIRED
from arche.security import PERM_EDIT
from arche.security import PERM_VIEW
from arche.views.base import BaseForm
from arche.views.base import BaseView
from arche_m2m.views.survey import BaseSurveySection
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotFound
from pyramid.traversal import resource_path
from pyramid.view import view_config
from pyramid.view import view_defaults
from repoze.catalog.query import Eq
import colander
import deform

from m2m_feedback import _
from m2m_feedback.interfaces import IFeedbackThreshold
from m2m_feedback.interfaces import IRuleSet
from m2m_feedback.interfaces import ISurveyFeedback
from m2m_feedback.models import get_all_choices
from m2m_feedback.models import get_relevant_threshold
from m2m_feedback.schemas import get_choice_values_appstruct
from m2m_feedback.schemas import get_choice_values_schema
from m2m_feedback.interfaces import IScoreHandler


@view_defaults(context = IRuleSet, permission = PERM_VIEW)
class RuleSetView(BaseView):

    @view_config(name = 'view', renderer = 'm2m_feedback:templates/rule_set.pt')
    def main_view(self):
        return {}

    def get_referenced_questions(self):
        results = []
        for uid in self.context.referenced_questions:
            results.append(self.resolve_uid(uid))
        return results

    def get_questions(self, questions):
        path = resource_path(questions)
        return self.catalog_search(resolve = True,
                                   language = self.request.locale_name,
                                   path = path,
                                   type_name = 'Question')

    def get_choices(self, question, only_from_type = False):
        return get_all_choices(question, self.request, only_from_type = only_from_type)


@view_config(context = IRuleSet,
             name = 'bulk_select',
             permission = PERM_EDIT,
             renderer = 'arche:templates/form.pt')
class BulkSelect(BaseForm):
    type_name = 'RuleSet'
    schema_name = 'bulk_select'

    @property
    def buttons(self):
        return (deform.Button('filter', title = _("Filter")), self.button_cancel)

    def filter_success(self, appstruct):
        return HTTPFound(location = self.request.resource_url(self.context, 'bulk_edit', query = appstruct))


@view_config(context = IRuleSet,
             name = 'bulk_edit',
             permission = PERM_EDIT,
             renderer = 'arche:templates/form.pt')
class BulkEdit(BaseForm):

    @property
    def question_type(self):
        qt = self.resolve_uid(self.request.GET.get('question_type', ''))
        if not qt:
            raise HTTPNotFound(_("Question type not found"))
        return qt

    @property
    def tag(self):
        return self.request.GET.get('tag', '')

    def get_schema(self):
        schema = get_choice_values_schema(self.question_type, self.request)
        schema.title = _("Bulk edit ${count} question(s) at once",
                         mapping = {'count': len(self.get_question_docids())})
        schema.description = _("bulk_edit_description",
                               default = "Warning: This will overwrite any previous values!")
        return schema

    def get_referenced_questions(self):
        """ I.e. Questions - the container object. """
        results = []
        for uid in self.context.referenced_questions:
            results.append(self.resolve_uid(uid))
        return results

    def get_question_docids(self):
        docids = set()
        for questions in self.get_referenced_questions():
            query = Eq('path', resource_path(questions))
            query &= Eq('type_name', 'Question')
            query &= Eq('question_type', self.question_type.uid)
            if self.tag:
                query &= Eq('tags', self.tag)
            docids.update(tuple(self.catalog_query(query, resolve = False)))
        return docids

    def save_success(self, appstruct):
        choices = self.question_type.get_choices(self.request.locale_name)
        for choice in choices:
            if choice.cluster not in appstruct:
                raise HTTPForbidden("Saved data did not contain correct references to the choice: %r" % choice)
        questions = tuple(self.request.resolve_docids(self.get_question_docids()))
        for question in questions:
            for choice in choices:
                self.context.set_choice_score(question, choice, appstruct[choice.cluster])
        self.flash_messages.add(_("${count} questions updated.",
                                  mapping = {'count': len(questions)}))
        return HTTPFound(location = self.request.resource_url(self.context, 'view'))

    def cancel_success(self, *args):
        return HTTPFound(location = self.request.resource_url(self.context, 'view'))


@view_config(context = IRuleSet,
             name = 'edit_question',
             permission = PERM_EDIT,
             renderer = 'arche:templates/form.pt')
class SingleEdit(BaseForm):

    @reify
    def question(self):
        que = self.resolve_uid(self.request.GET.get('uid', ''))
        if not que:
            raise HTTPNotFound(_("Question not found"))
        return que

    def appstruct(self):
        return get_choice_values_appstruct(self.context, self.question, self.request)

    def get_schema(self):
        schema = get_choice_values_schema(self.question, self.request)
        schema.title = self.question.title
        schema.description = _("Individual scores for this question")
        return schema

    def save_success(self, appstruct):
        choices = self.question.get_choices(self.request.locale_name)
        for choice in choices:
            if choice.cluster not in appstruct:
                raise HTTPForbidden("Saved data did not contain correct references to the choice: %r" % choice)
        for choice in choices:
            self.context.set_choice_score(self.question, choice, appstruct[choice.cluster])
        self.flash_messages.add(_("Saved"))
        return HTTPFound(location = self.request.resource_url(self.context, 'view'))

    def cancel_success(self, *args):
        return HTTPFound(location = self.request.resource_url(self.context, 'view'))


@view_config(context = ISurveyFeedback,
             name = 'info_panel',
             permission = PERM_VIEW,
             renderer = 'm2m_feedback:templates/feedback_info_panel.pt')
class SurveyFeedbackInfoPanel(BaseView):

    __call__ = lambda x: {}


@view_config(context = ISurveyFeedback,
             permission = NO_PERMISSION_REQUIRED,
             renderer = "m2m_feedback:templates/survey_feedback.pt")
@view_config(context = ISurveyFeedback,
             name = 'view',
             permission = PERM_VIEW,
             renderer = "m2m_feedback:templates/survey_feedback.pt")
class SurveyFeedbackForm(BaseSurveySection):

    @property
    def main_tpl(self):
        """ Use different template depending on who the user is.
        Regular participants get the stripped template without any other controls.
        """
        if self.show_manager_controls:
            return 'arche:templates/master.pt'
        return 'arche_m2m:templates/master_stripped.pt'

    @reify
    def show_manager_controls(self):
        return not self.participant_uid and self.request.has_permission(PERM_VIEW)

    @reify
    def ruleset(self):
        return self.resolve_uid(self.context.ruleset, perm = None)

    @reify
    def section(self):
        return self.resolve_uid(self.context.section, perm = None)

    @reify
    def score(self):
        return self.request.registry.getMultiAdapter([self.ruleset, self.request], IScoreHandler)

    @reify
    def max_score(self):
        return self.score.max_score(self.section, self.participant_uid)

    @reify
    def participant_score(self):
        return self.score.participant_score(self.section, self.participant_uid)

    def get_percentage(self, score):
        try:
            return (Decimal(score) / Decimal(self.max_score)) * 100
        except InvalidOperation:
            return 0

    def get_relevant_threshold(self, percentage = None):
        if percentage is None:
            percentage = self.get_percentage(self.participant_score)
        return get_relevant_threshold(self.context, percentage)

    def get_schema(self):
        return colander.Schema()

    def get_questions(self):
        results = []
        for qid in self.section.question_ids:
            docids = self.catalog_search(cluster = qid, language = self.request.locale_name)
            #Only one or none
            for question in self.resolve_docids(docids, perm = None):
                results.append(question)
        return results

    def get_picked_choice_score(self, section, question):
        choice = self.request.get_picked_choice(section, question, self.participant_uid)
        if choice and self.ruleset:
            return self.ruleset.get_choice_score(question, choice)

    def get_highest_choice_score(self, question):
        return self.score.get_highest_choice_score(question)

    def get_sort_by_hq(self, questions, reverse):
        """ parameters:
                - questions : iterable of some kind
                - reverse : boolean
            return a list of tuples sorted by the difference between the highest_score and the participant_score
        """
        #FIXME: Make it possible to set the number of shown scores
        #FIXME: Right now the same question could show up in both columns
        #FIXME: Handle situations where there are only bad or only good
        #FIXME: Check that it works properly with omitted question choices.
        result = []
        for q in questions:
            high_score = self.get_highest_choice_score(q)
            part_score = self.get_picked_choice_score(self.section, q)
            if isinstance(high_score, int) and isinstance(part_score, int):
                diff = high_score - part_score
                result.append((q, high_score, part_score, diff))
        return sorted(result, key = lambda result: result[3], reverse=reverse)[:3]

    def get_thresholds(self):
        """ Returns all contained thresholds sorted on percentage. """
        return sorted([x for x in self.context.values() if IFeedbackThreshold.providedBy(x)], key = lambda x: x.percentage)

    def next_success(self, appstruct):
        next_section = self.next_section()
        #Do stuff if finished
        if not next_section:
            return HTTPFound(location = self.link(self.context.__parent__, 'done'))
        return HTTPFound(location = self.link(next_section))

    def previous_success(self, appstruct):
        return self.go_previous()

    def go_previous(self, *args):
        previous = self.previous_section()
        if previous is None:
            return HTTPFound(location = self.link(self.context.__parent__, 'do'))
        return HTTPFound(location = self.link(previous))

    previous_failure = go_previous

def includeme(config):
    config.scan()
