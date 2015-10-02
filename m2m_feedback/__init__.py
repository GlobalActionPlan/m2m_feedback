from pyramid.i18n import TranslationStringFactory


_ = TranslationStringFactory('m2m_feedback')


def includeme(config):
    config.include('.models')
    config.include('.schemas')
    config.include('.views')
