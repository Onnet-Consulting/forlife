/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

odoo.define("pos_fast_loading.pos_close_popup", function (require) {
    "use strict";

    const Registries = require("point_of_sale.Registries");

    const ClosePosPopup = require("point_of_sale.ClosePosPopup");


    const FastLoadClosePosPopup = (ClosePosPopup) =>
        class extends ClosePosPopup {

            async closeSession() {
                if (this.env.pos.config.enable_pos_longpolling && $('.session_update').length) {
                    $('.session_update').click();
                }
                super.closeSession()
            }
        };
    Registries.Component.extend(ClosePosPopup, FastLoadClosePosPopup);
});
