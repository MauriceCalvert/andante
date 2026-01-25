"""Generate head motifs.

NOTE: This script required the deleted motifs/ module.
The new 6-layer architecture uses pre-defined arrivals from YAML config
rather than generated motifs.

To generate music, use:
    python -m scripts.run_pipeline invention c_major default
"""
import sys


def main() -> int:
    print("generate_heads.py is deprecated.")
    print("")
    print("The new architecture uses pre-defined schema arrivals from YAML config")
    print("rather than generated motifs.")
    print("")
    print("To generate music, use:")
    print("    python -m scripts.run_pipeline invention c_major default")
    return 1


if __name__ == "__main__":
    sys.exit(main())
