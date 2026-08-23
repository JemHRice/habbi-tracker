"""Allow `python -m app.seed` to run the loader."""

import sys

from app.seed.seed import main

sys.exit(main())
