from typing import TYPE_CHECKING

from .helpers import (
    can_execute_action,
    safe_reason,
    add_logging,
    col,
    mdr,
)

from .converters import BanEntryConverter

if TYPE_CHECKING:
    from typing import Union as TargetVerifier

    # I do this so my IDE doesn't complain about the
    # TargetVerifier converter. but idk tho it's bad.
    # CHAI find a better way to do this please.
else:
    from .converters import TargetVerifier

from .time import (
    Time,
    FutureTime,
    HumanTime,
    ShortTime,
    UserFriendlyTime,
    human_timedelta,
    human_join
)

from .base_cog import DuckCog
from .context import DuckContext
from .errorhandler import HandleHTTPException

# So the linter doesn't suggest random crap!
# Don't * import please :pleadCry: thx.

