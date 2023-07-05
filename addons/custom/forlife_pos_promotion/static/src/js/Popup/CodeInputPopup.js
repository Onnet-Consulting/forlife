odoo.define('forlife_pos_promotion.CodeInputPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');
    const { useListener } = require("@web/core/utils/hooks");

    const { onMounted, useRef, useState } = owl;

    // formerly TextInputPopupWidget
    class CodeInputPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            this.state = useState({ inputValue: this.props.startingValue });
            this.inputRef = useRef('input');
            useListener('confirm-code', () => this.confirm());
            useListener('cancel-code', () => this.cancel());
            onMounted(this.onMounted);
        }
        onMounted() {
            this.inputRef.el.focus();
        }
        getPayload() {
            return this.state.inputValue;
        }
        onInputKeyDownUp(ev) {
            if (ev.key === "Enter" && ev.target.value.trim() !== '') {
                this.trigger('confirm-code');
            } else if  (ev.key === "Escape" && ev.target.value.trim() !== '') {
                this.trigger('cancel-code');
            } else {
                const pattern = 'ABCDOEFGHIJKLMNPQRSTUVWXYZ0123456789-'
                let value = ev.target.value.toUpperCase();
                let newValue = ''
                for (var i = 0; i < value.length; i++) {
                    if (pattern.includes(value.charAt(i))) {
                        newValue += value.charAt(i);
                    };
                };
                ev.target.value = newValue;
            };
        }
    }
    CodeInputPopup.template = 'CodeInputPopup';
    CodeInputPopup.defaultProps = {
        confirmText: _lt('Ok'),
        cancelText: _lt('Cancel'),
        title: '',
        body: '',
        startingValue: '',
        placeholder: '',
    };

    Registries.Component.add(CodeInputPopup);

    return CodeInputPopup;
});
