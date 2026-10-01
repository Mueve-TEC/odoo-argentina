odoo.define('l10n_ar_point_of_sale.models', function (require) {
    "use strict";

    const { Order } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const defaultToInvoice = (pos) => {
        const value = pos.config.l10n_ar_default_to_invoice;
        return value === undefined ? true : value;
    };

    const L10nARPointOfSaleOrder = (Order) => class L10nARPointOfSaleOrder extends Order {
        constructor(obj, options) {
            super(...arguments);
            // New orders follow the "Invoice by default" POS setting. The
            // cashier can still turn the toggle off on the payment screen.
            if (!(options && options.json)) {
                this.to_invoice = defaultToInvoice(this.pos);
            }
        }
        //@override
        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            // Keep the value saved with the order, falling back to the POS
            // setting for orders that don't carry it yet.
            this.to_invoice = json.to_invoice === undefined ? defaultToInvoice(this.pos) : json.to_invoice;
        }
    };
    Registries.Model.extend(Order, L10nARPointOfSaleOrder);
});
