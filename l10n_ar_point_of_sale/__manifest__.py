{
    'name': 'l10n_ar_point_of_sale',
    'version': '16.0.1.4.0',
    'category': 'Accounting',
    'summary': 'Point of Sale',
    'depends': ['account','l10n_ar','l10n_ar_afipws_fe','point_of_sale'],
    'data': [
        'l10n_ar_point_of_sale.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'l10n_ar_point_of_sale/static/src/css/l10n_ar_point_of_sale.css',
            'l10n_ar_point_of_sale/static/src/js/models.js',
        ],
    },
    'demo': [
        ],
    'css': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
