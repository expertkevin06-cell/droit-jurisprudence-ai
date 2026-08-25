#!/usr/bin/env python3
"""
Envoie les notifications en attente.

À utiliser avec un vrai service de push en production.
"""

import sys
import os

backend_dir = os.path.join(os.getcwd(), "backend")
sys.path.append(backend_dir)

import notify


def main():
    count = notify.send_pending_notifications()
    print(f"{count} notification(s) traitée(s).")


if __name__ == "__main__":
    main()
