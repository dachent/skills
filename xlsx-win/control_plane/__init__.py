"""xlsx-win v2 control plane: the LLM-facing job/result contract.

Scope note: everything in this package is contract-only. No module here opens
Excel, calls COM, or touches openpyxl. That work belongs to issue #36.
"""
