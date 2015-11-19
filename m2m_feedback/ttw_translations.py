from arche_ttw_translation.models import Translatable

ttwt = Translatable()

ttwt['result_section'] = "Result of the section"
ttwt['score_display'] = "${participant_score} of ${max_score} points"
ttwt['highest_score'] = "Highest score"
ttwt['improvement_potential'] = "What you can improve"

def includeme(config):
    config.register_ttwt(ttwt)
