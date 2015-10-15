from arche.interfaces import IBase
from arche.interfaces import IContent


class IRuleSet(IContent):
    """ Keeps track of values for different choices for questions. """


class ISurveyFeedback(IContent):
    """ Gives feedback based on a users replies on previous sections.
        Must be attached to a scorecard to work.
    """

class IFeedbackThreshold(IBase):
    """ Give feedback to someone doing a survey based on a threshold.
    """