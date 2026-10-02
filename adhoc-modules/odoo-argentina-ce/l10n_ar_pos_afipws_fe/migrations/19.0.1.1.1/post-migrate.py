def migrate(cr, version):
    # Force POS clients to reset their IndexedDB config cache.
    #
    # This version adds the ``l10n_ar_default_to_invoice`` field on pos.config.
    # POS browsers that cached the config before the upgrade keep the stale
    # record (on reload into an already-open session the server ``load_data``
    # is skipped) and the new field reads as undefined in the frontend, which
    # makes orders default back to invoiced. Bumping ``last_data_change`` makes
    # every client whose cached data is older than this timestamp reset its
    # local cache and re-fetch the configuration on the next load.
    cr.execute("UPDATE pos_config SET last_data_change = (now() AT TIME ZONE 'utc')")
