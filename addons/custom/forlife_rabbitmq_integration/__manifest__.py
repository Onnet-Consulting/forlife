# -*- coding: utf-8 -*-
{
    'name': "RabbitMQ Integration",

    'summary': """""",

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",

    'category': 'Tools',
    'version': '16.0.1.0.0',

    'depends': [
        'queue_job',
        'forlife_base',
        'forlife_customer_card_rank',
        'forlife_pos_point_order',
    ],
    'auto_install': True,

    'data': [
        'security/ir.model.access.csv',
        'data/rabbitmq_connection_data.xml',
        'data/rabbitmq_queue_data.xml',
        'views/rabbitmq_connection_views.xml',
        'views/rabbitmq_queue_views.xml',
        'views/menuitem.xml',
    ],
    'external_dependencies': {
        'python': ['pika'],
    },
}
