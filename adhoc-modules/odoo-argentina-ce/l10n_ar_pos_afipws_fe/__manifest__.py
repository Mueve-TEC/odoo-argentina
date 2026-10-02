# pylint: disable=missing-module-docstring,pointless-statement
{
    "name": "Punto de venta Factura Electrónica Argentina",
    "version": "19.0.1.1.1",
    "category": "Localization/Argentina",
    "author": "Mueve, ADHOC SA, Filoquin",
    "website": "https://mueve.org.ar/",
    "license": "AGPL-3",
    "summary": "",
    "depends": [
        "l10n_ar_fiscal_ws_fe",
        "point_of_sale",
    ],
    "external_dependencies": {},
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "demo": [],
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_ar_pos_afipws_fe/static/src/app/**/*",
        ],
    },
    "images": [],
    "installable": True,
    "auto_install": False,
    "application": False,
}
