odoo.define('forlife_pos_promotion.db', function (require) {
    'use strict';

    const PosDB = require('point_of_sale.DB');
    PosDB.include({
            get_partner_write_date: function(){
                date = new Date()
                return this.partner_write_date || "1970-01-01 00:00:00";
            },
    });
});