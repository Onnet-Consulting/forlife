odoo.define('forlife_pos_promotion.db', function (require) {
    'use strict';

    const PosDB = require('point_of_sale.DB');
    PosDB.include({
            get_partner_write_date: function(){
                var d = new Date();
                var today = String(d.getFullYear()) + '-' + String(d.getMonth()+1) + '-' + String(d.getDay()) + ' 00:00:00';
                return this.partner_write_date || today;
            },
    });
});
