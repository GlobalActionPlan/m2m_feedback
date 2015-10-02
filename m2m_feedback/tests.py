from __future__ import unicode_literals
from unittest import TestCase

from arche.testing import barebone_fixture
from pyramid import testing
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject

from m2m_feedback.interfaces import IRuleSet


def _fixture_with_questions(root):
    from arche_m2m.models.question import Question
    from arche_m2m.models.question_type import Choice
    from arche_m2m.models.question_type import QuestionType
    from arche_m2m.models.question_types import QuestionTypes
    from arche_m2m.models.questions import Questions
    root['questions'] = Questions()
    root['qtypes'] = QuestionTypes()
    root['qtypes']['qt1'] = qt1 = QuestionType(uid = 'qt_uid', input_widget = 'checkbox_multichoice_widget')
    qt1['c1'] = Choice(cluster = 'a', uid = 'c_uid1', language = 'sv')
    qt1['c2'] = Choice(cluster = 'a', uid = 'c_uid2', language = 'en')
    qt1['c3'] = Choice(cluster = 'b', uid = 'c_uid3', language = 'sv')
    root['questions']['q1'] = Question(question_type = 'qt_uid', cluster = 'q_cluster')


class RuleSetTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from m2m_feedback.models import RuleSet
        return RuleSet

    def _fixture(self):
        root = barebone_fixture(self.config)
        _fixture_with_questions(root)
        return root

    def test_verify_class(self):
        verifyClass(IRuleSet, self._cut)

    def test_verify_object(self):
        verifyObject(IRuleSet, self._cut())

    def test_choice_score(self):
        root = self._fixture()
        question = root['questions']['q1']
        choice = root['qtypes']['qt1']['c1']
        obj = self._cut()
        obj.set_choice_score(question, choice, 1)
        self.assertEqual(obj.get_choice_score(question, choice), 1)
