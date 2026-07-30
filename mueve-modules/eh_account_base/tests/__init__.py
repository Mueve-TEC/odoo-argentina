# Phase 1 test plan:
#
# Functional unit tests:
#
# Integration tests (require an installed account module and demo data):
#
# Performance / pressure scaffolding (post_install tag, gated on perf threshold):
from . import (
    test_account_move_report,  # branded Journal Entry PDF render regression
    test_cache_invalidation,  # account.move state changes bump version
    test_dynamic_report,  # orchestrator render path and cache behaviour
    test_move_seal,
    test_net_guard,
    test_payload_codec,  # zlib JSON codec round trip
    test_perf_sql_builder,
    test_posted_line_edit_invalidation,  # posted line edits bump version
    test_privilege_groups,  # new privilege groups, implications, ACL pointers
    test_report_execution,  # audit model lifecycle and hashing
    test_report_fold_state,
    test_report_wizard,  # wizard build_options and export action
    test_sql_builder_integration,  # builder executes against real data
    test_sql_builder_unit,  # builder produces correct SQL/params
    test_xlsx_writer,  # XLSX writer shape and formats
)
