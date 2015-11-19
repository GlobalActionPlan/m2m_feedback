from pyramid.i18n import TranslationStringFactory


_ = TranslationStringFactory('m2m_feedback')


def includeme(config):
    config.include('.models')
    config.include('.schemas')
    config.include('.views')
    config.include('.fanstatic_lib')
    config.include('.ttw_translations')
    config.add_static_view('m2m_feedback', 'm2m_feedback:static')
