from zope.interface import Attribute
from zope.interface import Interface

from arche.interfaces import IBase
from arche.interfaces import IContent


class IRuleSet(IContent):
    """ Keeps track of values for different choices for questions. """


class IScoreHandler(Interface):
    context = Attribute("RuleSet object wrapped")
    request = Attribute("Current request")

    def __init__(context, request):
        """ Multi-adapter. context is always a RuleSet object. """

    def max_score(section, participant_uid):
        """
        :param section: SurveySection instance.
        :param participant_uid: Participants UID.
        :return: Maximum possible score considering the participants choices
            and any questions that should be omitted.
        :rtype: int
        """

    def participant_score(section, participant_uid):
        """
        :param section: SurveySection instance.
        :param participant_uid: Participants UID.
        :return: Participants score, takes into account if some questions should be omitted.
        :rtype: int
        """

    def handle_question(section, question, participant_uid):
        """
        :param section: SurveySection instance
        :param question: Question instance
        :param participant_uid: Participants UID.
        :return: Should the question be handled for this particular participant?
            Considering what kind of widget it has and the omit-setting.
        :rtype: bool
        """

    def handle_choice(choice):
        """
        :param choice: Choice instance
        :return: Checks if choice should be omitted or not.
        :rtype: bool
        """

    def get_picked_choice_score(section, question, participant_uid):
        """
        :param section: SurveySection instance
        :param question: Question instance
        :param participant_uid: Participants UID.
        :return: Picked choice score or None
        :rtype: int or None
        """

    def get_highest_choice_score(question):
        """
        :param question: Question instance
        :return: Highest possible score for this question, or 0
        :rtype: int
        """

    def get_current_average(section):
        """
        Calculate average score, in percent!
        (It's not sensible to do it any other way since some questions might be omitted)

        :param section: SurveySection instance
        :return: Each iteration will return one participants max, current and percentage as:
            (<max>, <current>, <percentage>)
        :rtype: generator
        """

class ISurveyFeedback(IContent):
    """ Gives feedback based on a users replies on previous sections.
        Must be attached to a scorecard to work.
    """

class IFeedbackThreshold(IBase):
    """ Give feedback to someone doing a survey based on a threshold.
    """