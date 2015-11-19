from arche_ttw_translation.models import Translatable

ttwt = Translatable()

#ttwt['start_btn'] = 'Start'
#ttwt['next_btn'] = 'Next'
#ttwt['previous_btn'] = 'Previous'
#ttwt['done'] = 'Done'
#ttwt['participant_done_text'] = 'Thank you for filling out the survey. In case you need to change anything, simply press the button below.'
#ttwt['participate_btn'] = 'Participate in the survey'
#ttwt['email_sent'] = 'Email sent successfully'
#ttwt['link_to_start_survey'] = 'Link to start survey'

ttwt['result_section'] = "Result of the section"
ttwt['score_display'] = "${participant_score} of ${max_score} points"
ttwt['highest_score'] = "Highest score"
ttwt['improvement_potential'] = "What you can improve"

def includeme(config):
    config.register_ttwt(ttwt)
