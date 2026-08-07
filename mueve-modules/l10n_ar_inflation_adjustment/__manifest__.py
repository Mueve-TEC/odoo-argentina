{
    'name': "Argentina - Ajuste por Inflación",
    'summary': """
        Ajuste por inflación contable para cierre de ejercicio fiscal argentino.""",
    'author': "Mueve",
    "website": "https://mueve.org.ar/",
    'category': 'Accounting',
    'version': "18.0.1.0.0",
    'license': 'AGPL-3',
    'depends': [
        'account',
        'l10n_ar',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/account_account_tag_data.xml',
        'data/inflation_adjustment_index_data.xml',
        'data/ir_actions_server_data.xml',
        'views/inflation_adjustment_index_views.xml',
        'views/account_account_views.xml',
        'wizards/inflation_adjustment_wizard_view.xml',
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'post_init_hook': 'post_init_hook',
}
