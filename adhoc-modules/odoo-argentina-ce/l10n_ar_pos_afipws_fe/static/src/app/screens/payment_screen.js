/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    onMounted() {
        const order = this.pos.getOrder();
        const shouldInvoice = order?.to_invoice;
        super.onMounted(...arguments);
        // After super, l10n_ar_pos may have forced to_invoice=true for Argentinean companies.
        // Reset it to false if the config says so and the order wasn't already marked for invoicing.
        if (this.pos.config.l10n_ar_default_to_invoice === false && !shouldInvoice) {
            this.pos.getOrder().to_invoice = false;
        }
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
