# -*- coding: utf-8 -*-
{
    'name': 'Pos warning',
    'version': '1.0.1',
    'category': 'Sales/Point of Sale',
    'sequence': 40,
    'summary': 'User-friendly PoS interface for shops and restaurants',
    'depends': ['point_of_sale'],
    'data': [
    ],
    'demo': [
        'data/point_of_sale_demo.xml',
    ],
    'installable': True,
    'application': True,
    'website': 'on.net.vn',
    'assets': {
        # This bundle includes the main pos assets.
        'point_of_sale.assets': [
            'point_of_sale/static/src/scss/pos_variables_extra.scss',
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            ('include', 'web._assets_primary_variables'),
            'web/static/lib/bootstrap/scss/_functions.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/fonts/fonts.scss',
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/lib/daterangepicker/daterangepicker.css',
            'point_of_sale/static/src/scss/pos.scss',
            'point_of_sale/static/src/css/pos_receipts.css',
            'point_of_sale/static/src/css/popups/product_info_popup.css',
            'point_of_sale/static/src/css/popups/common.css',
            'point_of_sale/static/src/css/popups/cash_opening_popup.css',
            'point_of_sale/static/src/css/popups/closing_pos_popup.css',
            'point_of_sale/static/src/css/popups/money_details_popup.css',
            'web/static/src/legacy/scss/fontawesome_overridden.scss',

            # Here includes the lib and POS UI assets.
            'point_of_sale/static/lib/**/*.js',
            'web_editor/static/lib/html2canvas.js',
            'point_of_sale/static/src/js/**/*.js',
            'web/static/lib/zxing-library/zxing-library.js',
            'point_of_sale/static/src/xml/**/*.xml',
        ],
    },
    'license': 'LGPL-3',
}
