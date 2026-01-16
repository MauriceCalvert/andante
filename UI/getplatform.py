import sys
import os


def get_platform():
    """Returns: 'windows', 'macos', 'linux', 'colab', or 'unknown'"""

    # Colab check first (it's Linux underneath)
    if 'google.colab' in sys.modules:
        return 'colab'

    # Jupyter/IPython check (optional, if you need it)
    # if 'ipykernel' in sys.modules:
    #     return 'jupyter'

    # Standard platform detection
    if sys.platform == 'win32':
        return 'windows'
    elif sys.platform == 'darwin':
        return 'macos'
    elif sys.platform.startswith('linux'):
        return 'linux'

    return 'unknown'