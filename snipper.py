#!/usr/bin/env python3
"""
Legacy snipper.py entrypoint - DEPRECATED

This file has been refactored into a modular architecture.
Please use the new entrypoint instead:

    python -m snipper.main

The new architecture provides:
- Improved error handling and logging
- Modular, testable components
- Risk management and circuit breakers
- Configuration validation
- Structured logging with correlation IDs
- Dry-run mode for testing
- Better security practices

For migration help, see README.md and CONTRIBUTING.md
"""

import sys

def main():
    print("=" * 70)
    print("⚠️  DEPRECATED: This file has been refactored!")
    print("=" * 70)
    print()
    print("The monolithic snipper.py has been replaced with a modular architecture.")
    print()
    print("New usage:")
    print("  python -m snipper.main                    # Production mode")
    print("  python -m snipper.main --dry-run          # Test mode")
    print("  python -m snipper.main --status           # Status check")
    print()
    print("Benefits of the new architecture:")
    print("  ✅ Modular, testable components")
    print("  ✅ Comprehensive risk management")
    print("  ✅ Structured logging with correlation IDs")
    print("  ✅ Configuration validation")
    print("  ✅ Dry-run mode for safe testing")
    print("  ✅ Better error handling")
    print("  ✅ Security improvements")
    print()
    print("For more information:")
    print("  📖 README.md - Setup and usage guide")
    print("  🔒 SECURITY.md - Security guidelines")
    print("  🤝 CONTRIBUTING.md - Development guide")
    print()
    print("=" * 70)
    
    # Ask user if they want to run the new version
    try:
        response = input("Run the new version instead? (y/N): ").strip().lower()
        if response in ('y', 'yes'):
            import subprocess
            subprocess.run([sys.executable, '-m', 'snipper.main'] + sys.argv[1:])
        else:
            print("Please update your scripts to use: python -m snipper.main")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(1)

if __name__ == "__main__":
    main()