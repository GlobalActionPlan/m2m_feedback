# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from arche_m2m.interfaces import IQuestion
from arche_m2m.models.question import deferred_question_type_widget
from pyramid.traversal import resource_path
import colander
import deform

from m2m_feedback import _

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
    choices = list(question.get_choices(request.locale_name))
    if IQuestion.providedBy(question):
        docids = request.root.catalog.query("uid == '%s'" % question.question_type)[1]
        question_type = None
        #Generator
        for qt in request.resolve_docids(docids):
            question_type = qt
            choices.extend(question_type.get_choices(request.locale_name))
    for choice in choices:
        schema.add(colander.SchemaNode(colander.Int(),
                                       name = choice.cluster,
                                       title = choice.title))
    return schema


def includeme(config):
    config.add_content_schema('RuleSet', RuleSetSchema, ('add','edit', 'view'))
    config.add_content_schema('RuleSet', BulkSelectQuestionsSchema, 'bulk_select')