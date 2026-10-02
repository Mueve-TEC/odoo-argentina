/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    onMounted() {
        super.onMounted(...arguments);
        const order = this.pos.getOrder();
        // Core force-invoices refunds of invoiced orders (the ARCA credit note
        // needs to reference the original invoice). Let the "Invoice by
        // default" POS setting govern refunds too: when the option is off,
        // refunds are not invoiced by default.
        if (
            order?.isRefund &&
            order.lines[0]?.refunded_orderline_id?.order_id?.isToInvoice() &&
            this.pos.config.l10n_ar_default_to_invoice === false
        ) {
            order.to_invoice = false;
        }
    },
});
