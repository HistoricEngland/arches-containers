try:
    from .{{project}}.settings import *
except ImportError:
    pass

try:
    from .settings_docker import *
except ImportError:
    pass
