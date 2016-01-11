# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from arche.interfaces import ISchemaCreatedEvent
from arche_m2m.interfaces import ISurvey
from arche_m2m.interfaces import ISurveySection
from arche_m2m.models.i18n import deferred_translations_node
from arche_m2m.schemas.question import deferred_question_type_widget
from arche_m2m.schemas.question_type import EditChoiceSchema
from pyramid.traversal import find_interface
from pyramid.traversal import resource_path
import colander
import deform

from m2m_feedback import _
from m2m_feedback.models import get_all_choices


@colander.deferred
def referenced_questions_widget(node, kw):
    view = kw['view']
    query = "type_name == 'Questions'"
    values = []
    for obj in view.catalog_query(query, resolve = True, sort_index = 'sortable_title'):
        values.append((obj.uid, "%s (%s)" % (obj.title, resource_path(obj))))
    return deform.widget.CheckboxChoiceWidget(values = values)


class RuleSetSchema(colander.Schema):
    title = colander.SchemaNode(colander.String(),
                                title = _("Title"))
    referenced_questions = colander.SchemaNode(colander.Set(),
                                               title = _("Question sets to work with"),
                                               widget = referenced_questions_widget)


@colander.deferred
def referenced_ruleset_widget(node, kw):
    view = kw['view']
    query = "type_name == 'RuleSet'"
    values = [('', _("<Select>"))]
    for obj in view.catalog_query(query, resolve = True, sort_index = 'sortable_title'):
        values.append((obj.uid, "%s (%s)" % (obj.title, resource_path(obj))))
    return deform.widget.SelectWidget(values = values)

@colander.deferred
def referenced_section_widget(node, kw):
    context = kw['context']
    values = [('', _("<Select>"))]
    survey = find_interface(context, ISurvey)
    for obj in survey.values():
        if ISurveySection.providedBy(obj):
            values.append((obj.uid, obj.title))
    return deform.widget.SelectWidget(values = values)


class SurveyFeedbackSchema(colander.Schema):
    title = colander.SchemaNode(colander.String(),
                                translate = True,
                                translate_missing = "",
                                title = _("Title"))
    translations = deferred_translations_node
    ruleset = colander.SchemaNode(colander.String(),
                                  title = _("Ruleset"),
                                  widget = referenced_ruleset_widget,)
    section = colander.SchemaNode(colander.String(),
                                  title = _("Section to give feedback on"),
                                  description = _("feedback_schema_section_description",
                                                  default = "Must be a locally placed section. "
                                                  "If none exist you may need to add one first."),
                                  widget = referenced_section_widget,)


class FeedbackThresholdSchema(colander.Schema):
    percentage = colander.SchemaNode(colander.Int(),
                                     title = _("Percentage"),
                                     description = _("Above this increase"))
    title = colander.SchemaNode(colander.String(),
                                title = _("Title"),
                                description = _("One-word title for this status."))
    description = colander.SchemaNode(colander.String(),
                                title = _("In-depth description"),
                                description = _("threshold_description",
                                                default = "Any tips for participants who reach this level?"))
    colour = colander.SchemaNode(colander.String(),
                                 title = _("Colour"),
                                 description = _("rgb_colour_description",
                                                 default = "RGB colour codes. 6 letters or digits."),
                                 missing = "",
                                 validator = colander.Regex("^[a-fA-F0-9]{6}$",
                                                            msg =_("colour_regex_fail",
                                                                   default = "Must be 0-9 and a-f only, and exactly 6 chars.")))

@colander.deferred
def tag_select_widget(node, kw):
    view = kw['view']
    values = [('', _("All"))]
    tags = tuple(view.root.catalog['tags']._fwd_index.keys())
    values.extend([(x, x) for x in tags])
    return deform.widget.SelectWidget(values = values)


class BulkSelectQuestionsSchema(colander.Schema):
    question_type = colander.SchemaNode(colander.String(),
                                        title = _("Question type"),
                                        widget = deferred_question_type_widget,)
    tag = colander.SchemaNode(colander.String(),
                              title = _("Tag"),
                              missing = "",
                              widget = tag_select_widget,)


def get_choice_values_schema(question, request):
    """ Append all relevant choices for question.
        question is either a QuestionType or a Question object.
        If it's a Question object, fetch all choices from
        the referenced question type too.
    """
    schema = colander.Schema()
    choices = get_all_choices(question, request, include_omitted = True)
    for choice in choices:
        schema.add(colander.SchemaNode(colander.Int(),
                                       name = choice.cluster,
                                       title = choice.title))
    return schema

def get_choice_values_appstruct(ruleset, question, request):
    """ Fetch any existing scores for choices related to this question or question type.
    """
    appstruct = {}
    for choice in get_all_choices(question, request, include_omitted = True):
        value = ruleset.get_choice_score(question, choice)
        if value != None:
            appstruct[choice.cluster] = value
    return appstruct

def add_nocount_option_to_choices(schema, event):
    schema.add(colander.SchemaNode(colander.Bool(),
                                   name = 'omit_from_score_count',
                                   title = _("Omit from score count"),
                                   default = False,
                                   missing = False))

def includeme(config):
    config.add_content_schema('RuleSet', RuleSetSchema, ('add','edit', 'view'))
    config.add_content_schema('RuleSet', BulkSelectQuestionsSchema, 'bulk_select')
    config.add_content_schema('SurveyFeedback', SurveyFeedbackSchema, ('add', 'edit', 'view'))
    config.add_content_schema('FeedbackThreshold', FeedbackThresholdSchema, ('add', 'edit', 'view'))
    config.add_subscriber(add_nocount_option_to_choices, [EditChoiceSchema, ISchemaCreatedEvent])