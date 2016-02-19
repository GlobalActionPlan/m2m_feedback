from __future__ import unicode_literals
from unittest import TestCase

from arche.testing import barebone_fixture
from arche.testing import init_request_methods
from arche_m2m.testing import question_fixture
from pyramid import testing
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject
from pyramid.request import apply_request_extensions

from m2m_feedback.interfaces import IRuleSet
from m2m_feedback.interfaces import IScoreHandler


def _fixture_feedback_section(root):
    from m2m_feedback.models import RuleSet
    from m2m_feedback.models import SurveyFeedback
    from arche_m2m.models.survey import Survey
    from arche_m2m.models.survey_section import SurveySection
    root['ruleset'] = rs = RuleSet(referenced_questions = (root['questions'].uid,))
    qt1 = root['qtypes']['qt1']
    q1 = root['questions']['q1']
    #Just one of each!
    #q1 max score 4
    rs.set_choice_score(q1, qt1['c1'], 1) #a
    rs.set_choice_score(q1, qt1['c2'], 1) #a
    rs.set_choice_score(q1, qt1['c3'], 4) #b
    qt2 = root['qtypes']['qt2']
    q2 = root['questions']['q2']
    #q2 max score 8
    rs.set_choice_score(q2, qt2['c1'], 2) #c
    rs.set_choice_score(q2, q2['c2'], 4) #d
    rs.set_choice_score(q2, q2['c3'], 8) #e
    qt3 = root['qtypes']['qt3']
    q3 = root['questions']['q3']
    #q3 max score 5
    rs.set_choice_score(q3, qt3['c1'], 4) #f
    rs.set_choice_score(q3, q3['c2'], 4) #f
    rs.set_choice_score(q3, q3['c3'], 5) #g
    root['survey'] = survey = Survey()
    survey['ss'] = ss = SurveySection()
    ss.question_ids = ['q_cluster', 'q_cluster2', 'q_cluster3']
    survey['feedback'] = SurveyFeedback(ruleset = rs.uid, section = ss.uid)

def _fixture_section_responses(root):
    #NOTE: only q_cluster3 has a question in english and corresponding choice translations!
    #See arche_m2m.testing.question_fixture
    section = root['survey']['ss']
    section.responses['part_1'] = {'q_cluster': 'b', 'q_cluster2': 'd', 'q_cluster3': 'f'}
    section.responses['part_2'] = {'q_cluster': 'a', 'q_cluster2': 'e', 'q_cluster3': 'g'}
    section.responses['part_3'] = {'q_cluster': '', 'q_cluster2': '', 'q_cluster3': ''}
    return section

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
        question_fixture(root)
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


class ScoreHandlerTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from m2m_feedback.models import ScoreHandler
        return ScoreHandler

    def _fixture(self):
        self.config.include('arche.testing')
        self.config.include('arche.testing.catalog')
        self.config.include('arche.testing.workflow')
        self.config.include('betahaus.viewcomponent')
        self.config.include('arche_m2m')
        self.config.include('m2m_feedback')
        root = barebone_fixture(self.config)
        question_fixture(root)
        _fixture_feedback_section(root)
        return root

    def test_verify_class(self):
        self.failUnless(verifyClass(IScoreHandler, self._cut))

    def test_verify_object(self):
        obj = self._cut(None, None)
        self.failUnless(verifyObject(IScoreHandler, obj))

    def test_get_current_average_en(self):
        root = self._fixture()
        section = _fixture_section_responses(root)
        request = testing.DummyRequest()
        apply_request_extensions(request)
        request.root = root
        obj = self._cut(root['ruleset'], request)
        result = tuple(obj.get_current_average(section))
        #part_1
        self.assertEqual(result[0][:2], [5, 4])
        #part_2
        self.assertEqual(result[1][:2], [5, 5])
        #part_3
        self.assertEqual(result[2][:2], [5, 0])

    def test_get_current_average_sv(self):
        root = self._fixture()
        section = _fixture_section_responses(root)
        self.config.registry.settings['default_locale_name'] = 'sv'
        request = testing.DummyRequest()
        self.assertEqual(request.locale_name, 'sv')
        apply_request_extensions(request)
        request.root = root
        obj = self._cut(root['ruleset'], request)
        result = tuple(obj.get_current_average(section))
        #part_1
        self.assertEqual(result[0][:2], [17, 12])
        #part_2
        self.assertEqual(result[1][:2], [17, 14])
        #part_3
        self.assertEqual(result[2][:2], [17, 0])

    def test_get_current_average_sv_some_picked_choices_omitted(self):
        root = self._fixture()
        section = _fixture_section_responses(root)
        #a, b en/sv
        root['qtypes']['qt1']['c1'].omit_from_score_count = True
        root['qtypes']['qt1']['c2'].omit_from_score_count = True
        root['qtypes']['qt1']['c3'].omit_from_score_count = True
        #c
        root['qtypes']['qt2']['c1'].omit_from_score_count = True
        self.config.registry.settings['default_locale_name'] = 'sv'
        request = testing.DummyRequest()
        apply_request_extensions(request)
        request.root = root
        obj = self._cut(root['ruleset'], request)
        result = tuple(obj.get_current_average(section))
        #part_1
        self.assertEqual(result[0][:2], [13, 8])
        #part_2
        self.assertEqual(result[1][:2], [13, 13])
        #part_3
        self.assertEqual(result[2][:2], [13, 0])


class UpdateChoiceSiblingsIntegrationTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _fixture(self):
        root = barebone_fixture(self.config)
        question_fixture(root)
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
        self.config.include('betahaus.viewcomponent')
        self.config.include('arche_m2m')
        self.config.include('m2m_feedback')
        root = barebone_fixture(self.config)
        question_fixture(root)
        _fixture_feedback_section(root)
        return root

    def _mk_view(self, locale_name = 'sv', **kw):
        root = self._fixture()
        request = testing.DummyRequest(locale_name = locale_name, **kw)
        init_request_methods(request)
        request.root = root
        return self._cut(root['survey']['feedback'], request)

    def test_get_questions(self):
        view = self._mk_view()
        questions = view.request.root['questions']
        self.assertEqual(view.get_questions(), [questions['q1'], questions['q2'], questions['q3']])

    def test_max_score(self):
        view = self._mk_view()
        self.assertEqual(view.max_score, 17)

    def test_participant_score(self):
        view = self._mk_view(params = {'uid': 'participant_uid'})
        section = view.request.root['survey']['ss']
        section.responses['participant_uid'] = {'q_cluster': 'a','q_cluster2': 'e', 'q_cluster3': 'f'}
        self.assertEqual(view.participant_score, 13)

    def test_get_highest_choice_score(self):
        view = self._mk_view()
        questions = view.root['questions']
        q1 = questions['q1']
        q2 = questions['q2']
        q3 = questions['q3']
        self.assertEqual(view.get_highest_choice_score(q1), 4)
        self.assertEqual(view.get_highest_choice_score(q2), 8)
        self.assertEqual(view.get_highest_choice_score(q3), 5)

    def test_display(self):
        view = self._mk_view(params = {'uid': 'participant_uid'})
        questions = view.request.root['questions']
        questions['q1'].title = "q1"
        questions['q2'].title = "q2"
        questions['q3'].title = "q3"
        section = view.request.root['survey']['ss']
        section.responses['participant_uid'] = {'q_cluster': 'a', 'q_cluster2': 'e', 'q_cluster3': 'f'}
        res = view.get_sort_by_hq([questions['q1'], questions['q2'], questions['q3']], False)
        self.assertEqual(res, [(questions['q2'], 8, 8, 0), (questions['q3'], 5, 4, 1), (questions['q1'], 4, 1, 3)])
        res = view.get_sort_by_hq([questions['q1'], questions['q2'], questions['q3']], True)
        self.assertEqual(res, [(questions['q1'], 4, 1, 3), (questions['q3'], 5, 4, 1), (questions['q2'], 8, 8, 0)])


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
