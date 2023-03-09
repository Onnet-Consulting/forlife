/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

export class SendHmrcButton extends Component {

    setup() {
        this.orm = useService("orm");
        this.title = this.env._t('Send Data to the HMRC Service');
        this.hmrcGovClientDeviceIdentifier = this.props.record.data.hmrc_gov_client_device_id;
    }

    async retrieveClientInfo() {

        if (!localStorage.getItem('hmrc_gov_client_device_id')) {
            localStorage.setItem('hmrc_gov_client_device_id', this.hmrc_gov_client_device_id);
        }

        const clientInfo = {
            'screen_width': screen.width,
            'screen_height': screen.height,
            'screen_scaling_factor': window.devicePixelRatio,
            'screen_color_depth': screen.colorDepth,
            'window_width': window.outerWidth,
            'window_height': window.outerHeight,
            'hmrc_gov_client_device_id': localStorage.getItem('hmrc_gov_client_device_id'),
        }

        await this.props.record.save();
        await this.orm.call(
            'l10n_uk.hmrc.send.wizard',
            'send',
            [this.props.record.resId, clientInfo]
        );
    }


}

SendHmrcButton.template = "l10n_uk_reports.SendHmrcButton";
registry.category('view_widgets').add('send_hmrc_button', SendHmrcButton);
