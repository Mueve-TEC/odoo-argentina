{
    'name': 'Fix Module Upgrade',
    'version': '16.0.1.0.0',
    'category': 'Technical',
    'summary': 'Fix button_immediate_upgrade TypeError in Odoo 16',
    'description': """
        This module fixes the TypeError that occurs when updating modules:
        "button_immediate_upgrade() takes 1 positional argument but 2 were given"
        
        This is a known issue in Odoo 16.0 where the method signature doesn't match
        the way it's called from the frontend.
    """,
    'author': 'Technical Fix',
    'depends': ['base'],
    'data': [],
    'installable': True,
    'auto_install': True,
    'application': False,
}
