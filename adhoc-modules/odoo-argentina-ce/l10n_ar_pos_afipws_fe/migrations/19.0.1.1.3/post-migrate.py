def migrate(cr, version):
    # Force POS clients to reset their IndexedDB config cache AGAIN.
    #
    # Version 19.0.1.1.2 attempted to add ``_load_pos_data_fields`` override
    # but broke the loading (empty fields list means "load all" in Odoo 19).
    # Reverted in 19.0.1.1.3. The field IS loaded automatically via ``read([])``.
    # This bump forces cache reset so clients pick up the field value correctly.
    cr.execute("UPDATE pos_config SET last_data_change = (now() AT TIME ZONE 'utc')")
