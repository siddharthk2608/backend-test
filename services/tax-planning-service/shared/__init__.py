# shared/__init__.py
"""Shared utilities for all services"""

from .database import Database, create_indexes
from .db_models import (
    TaxReturnDocument,
    TaxAnalysisDocument,
    UserDocument,
    model_to_dict,
    dict_to_model
)

__all__ = [
    'Database',
    'create_indexes',
    'TaxReturnDocument',
    'TaxAnalysisDocument',
    'UserDocument',
    'model_to_dict',
    'dict_to_model'
]
