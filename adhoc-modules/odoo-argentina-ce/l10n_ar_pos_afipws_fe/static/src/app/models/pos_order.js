/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(...arguments);
        const defaultObj = vals || {};
        // New orders follow the "Invoice by default" POS setting. Orders
        // loaded from the server keep the value saved on the record.
        // Fallback ``false``: a POS client with a stale cached config (e.g.
        // cached before this field existed) must not silently default new
        // orders to invoiced.
        if (defaultObj.to_invoice === undefined) {
            this.to_invoice = this.config.l10n_ar_default_to_invoice ?? false;
        }
    },
});
