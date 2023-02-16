odoo.define('forlife_pos_promotion.PromotionSelectionPopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

    const { useState } = owl;

    // formerly SelectionPopupWidget
    class ProgramSelectionPopup extends AbstractAwaitablePopup {

        setup() {
            super.setup();
            this.state = useState({ programs: [] });
//            this.state = useState({ selectedId: this.props.list.find((item) => item.isSelected) });
        }
        selectItem(itemId) {
            this.state.selectedId = itemId;
//            this.confirm();
        }
        /**
         * We send as payload of the response the selected item.
         *
         * @override
         */
        getPayload() {
//            const selected = this.props.programs.find((item) => this.state.selectedId === item.id);
//            return selected && selected.item;
        }
    }
    ProgramSelectionPopup.template = 'ProgramSelectionPopup';
    ProgramSelectionPopup.defaultProps = {
        cancelText: _lt('Cancel'),
        title: _lt('Select'),
        body: '',
        programs: [],
        confirmKey: false,
    };

    Registries.Component.add(ProgramSelectionPopup);

    return ProgramSelectionPopup;
});
