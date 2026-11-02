# 0002 Deterministic resource ids

Date: 2026-11-02. Status: accepted.

Ids are UUIDv5 over stable input keys (fixed namespace in `bundle.py`), so
re-exporting the same period produces identical resources. This keeps golden
tests exact and lets the receiving side de-duplicate. The Bundle id also
includes the build timestamp, so two exports stay distinguishable.
