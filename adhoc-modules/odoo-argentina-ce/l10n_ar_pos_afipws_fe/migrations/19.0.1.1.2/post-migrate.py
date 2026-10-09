def migrate(cr, version):
    # Force POS clients to reset their IndexedDB config cache AGAIN.
    #
    # Version 19.0.1.1.1 added the ``l10n_ar_default_to_invoice`` field but
    # forgot to include it in ``_load_pos_data_fields``, so the field never
    # reached the frontend config cache. Clients that cached the config after
    # that upgrade still have the field as ``undefined``. This bump forces a
    # fresh reload with the field now properly loaded.
    cr.execute("UPDATE pos_config SET last_data_change = (now() AT TIME ZONE 'utc')")
