import os

# shared.valkey_client refuses to import without a password; no connection is
# made until get_valkey_client() is called.
os.environ.setdefault("VALKEY_PASSWORD", "unit_test_password")
