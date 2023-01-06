odoo.define('forlife_point_of_sale.PosOpenedPopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _t } = require('web.core');
    const { parse } = require('web.field_utils');
    let rpc = require('web.rpc');
    const { useRef, useState } = owl;

    class PosOpenedPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            var self = this;
            self.pos_opened = useState({
                name: [],
                error: ""
            });
            rpc.query({
                model: 'store',
                method: 'get_pos_opened',
                args: [],
            }).then(function (pos_name) {
                self.pos_opened.name = pos_name[0]
            }, function (err, ev) {
                self.pos_opened.error = _t('Can\'t get all opened pos from backend')
            });
        }
    }
    PosOpenedPopup.template = 'forlife_point_of_sale.PosOpenedPopup';
    PosOpenedPopup.defaultProps = {
        cancelText: _t('Cancel'),
        title: _t('Store Status'),
    };

    Registries.Component.add(PosOpenedPopup);

    return PosOpenedPopup;
})