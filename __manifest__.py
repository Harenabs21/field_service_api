# -*- coding: utf-8 -*-
{
    'name': "Field Service API",

    'summary': "REST API for Field Service Integration in Odoo",

    'description': """
Long description of module's purpose
    """,

    'author': "Harena Sarobidy",
    'website': "https://github.com/Harenabs21",
    'category': 'Industry',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'industry_fsm'],

    # icon
    'icon': '/field_service_api/static/description/icon.png',

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/project_task.xml',
        'views/project_task_type.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
