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
    root['qtypes']['qt2'] = qt2 = QuestionType(uid = 'qt_uid2', input_widget = 'checkbox_multichoice_widget')
    qt1['c1'] = Choice(cluster = 'a', uid = 'c_uid1', language = 'sv')
    qt1['c2'] = Choice(cluster = 'a', uid = 'c_uid2', language = 'en')
    qt1['c3'] = Choice(cluster = 'b', uid = 'c_uid3', language = 'sv')
    qt2['c1'] = Choice(cluster = 'c', uid = 'c_uid4', language = 'sv')
    root['questions']['q1'] = Question(question_type = 'qt_uid', cluster = 'q_cluster', language = 'sv')
    root['questions']['q2'] = q2 = Question(question_type = 'qt_uid2', cluster = 'q_cluster2', language = 'sv')
    q2['c2'] = Choice(cluster = 'c', uid = 'c_uid5', language = 'en')
    q2['c3'] = Choice(cluster = 'd', uid = 'c_uid6', language = 'sv')

def _fixture_feedback_section(root):
    from m2m_feedback.models import RuleSet
    from m2m_feedback.models import SurveyFeedback
    from arche_m2m.models.survey import Survey
    from arche_m2m.models.survey_section import SurveySection
    root['ruleset'] = rs = RuleSet(referenced_questions = (root['questions'].uid,))
    qt1 = root['qtypes']['qt1']
    q1 = root['questions']['q1']
    #Just one of each!
    rs.set_choice_score(q1, qt1['c1'], 1) #a
    rs.set_choice_score(q1, qt1['c3'], 2) #b
    qt2 = root['qtypes']['qt2']
    q2 = root['questions']['q2']
    rs.set_choice_score(q2, qt2['c1'], 4) #c
    rs.set_choice_score(q2, q2['c3'], 8) #d
    root['survey'] = survey = Survey()
    survey['ss'] = ss = SurveySection()
    ss.question_ids = ['q_cluster', 'q_cluster2']
    survey['feedback'] = SurveyFeedback(ruleset = rs.uid, section = ss.uid)


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

    def test_choice_score_with_cluster_id(self):
        root = self._fixture()
        question = root['questions']['q1']
        choice = root['qtypes']['qt1']['c1']
        obj = self._cut()
        obj.set_choice_score(question, choice, 1)
        self.assertEqual(obj.get_choice_score(question.cluster, choice.cluster), 1)


class UpdateChoiceSiblingsIntegrationTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _fixture(self):
        root = barebone_fixture(self.config)
        _fixture_with_questions(root)
        return root

    def test_omit_from_score_count_updated(self):
        self.config.include('arche.testing')
        self.config.include('arche.models.catalog')
        self.config.include('arche_m2m.models.catalog')
        root = self._fixture()
        self.config.include('m2m_feedback.models')
        c1 = root['qtypes']['qt1']['c1']
        c2 = root['qtypes']['qt1']['c2']
        self.assertEqual(c1.omit_from_score_count, False)
        c1.update(omit_from_score_count = True)
        self.assertEqual(c1.omit_from_score_count, True)
        self.assertEqual(c2.omit_from_score_count, True)


class SurveyFeedbackFormTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from m2m_feedback.views import SurveyFeedbackForm
        return SurveyFeedbackForm

    def _fixture(self):
        self.config.include('arche.testing')
        self.config.include('arche.testing.catalog')
        self.config.include('arche.models.workflow')
        self.config.include('arche_m2m')
        root = barebone_fixture(self.config)
        _fixture_with_questions(root)
        _fixture_feedback_section(root)
        return root

    def _mk_view(self, locale_name = 'sv', **kw):
        root = self._fixture()
        request = testing.DummyRequest(locale_name = locale_name, **kw)
        request.root = root
        return self._cut(root['survey']['feedback'], request)

    def test_get_questions(self):
        view = self._mk_view()
        questions = view.request.root['questions']
        self.assertEqual(view.get_questions(), [questions['q1'], questions['q2']])

    def test_max_score(self):
        view = self._mk_view()
        self.assertEqual(view.max_score, 10)

    def test_participant_score(self):
        view = self._mk_view(params = {'uid': 'participant_uid'})
        section = view.request.root['survey']['ss']
        section.responses['participant_uid'] = {'q_cluster': 'a', 'q_cluster2': 'd'}
        self.assertEqual(view.participant_score, 9)


class GetRelevantThresholdTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _fut(self):
        from m2m_feedback.models import get_relevant_threshold
        return get_relevant_threshold

    def _fixture(self):
        from m2m_feedback.models import SurveyFeedback
        from m2m_feedback.models import FeedbackThreshold
        feedback = SurveyFeedback()
        feedback['a'] = FeedbackThreshold(title = 'A', percentage = 10)
        feedback['b'] = FeedbackThreshold(title = 'B', percentage = 30)
        feedback['c'] = FeedbackThreshold(title = 'C', percentage = 60)
        return feedback

    def test_get_0(self):
        context = self._fixture()
        self.assertEqual(self._fut(context, 0), None)

    def test_get_10(self):
        context = self._fixture()
        self.assertEqual(self._fut(context, 10), context['a'])

    def test_get_35(self):
        context = self._fixture()
        self.assertEqual(self._fut(context, 35), context['b'])

    def test_get_100(self):
        context = self._fixture()
        self.assertEqual(self._fut(context, 100), context['c'])
