"""結案與倉儲取件 (closures) module.

Ported from Role D's flat sync implementation (``app/routers/closures.py`` +
``app/store/closures.py``) into the canonical async modular structure:
``router.py`` (thin) → ``service.py`` (business logic) → ``repository.py``
(async DB queries).
"""
