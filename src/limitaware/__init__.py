"""LimitAware: provenance-preserving WQP result preparation.

Public API:
    from limitaware import contract, policies, canonical
    rows, header = contract.read_rows(path)
    records, summary = canonical.transform(rows, policy)
"""

__version__ = "0.1.4"
