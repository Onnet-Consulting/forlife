odoo.define('forlife_pos_layout.Chrome', function(require) {
    'use strict'

    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');

    const NamePosChrome = Chrome => class extends Chrome {
        //Get Nam POS
        get namePos() {
            return this.env.pos.config.name;
        }
    };

    Registries.Component.extend(Chrome, NamePosChrome);

    return Chrome;
});
