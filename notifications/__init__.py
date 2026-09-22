"""Atlas notifications — isolated preference and consent model (Stage 1).

This package is **not** imported by Phase 2. Feature flag
``ATLAS_NOTIFICATIONS_ENABLED`` is false by default. No HTTP routes.
No channels, delivery, or external services in this stage.
"""

from notifications.config import ATLAS_NOTIFICATIONS_ENABLED

__all__ = ["ATLAS_NOTIFICATIONS_ENABLED"]
