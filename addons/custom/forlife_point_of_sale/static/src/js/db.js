odoo.define('forlife_point_of_sale.DB', function (require) {
    "use strict";
    let PosDB = require('point_of_sale.DB');
    PosDB.include({
        limit: 40, // the maximum (40) number of results returned by a search
    })
});