# Minimal scheduler: runs every 5 minutes and updates signals.json
import time, traceback
from core.signals import compute_and_store_signals
def main():
    print('Scheduler started. Fetching signals every 5 minutes...')
    while True:
        try:
            compute_and_store_signals()
            print('Signals updated. Sleeping 300s...')
        except Exception as e:
            print('Error in scheduler:', e)
            traceback.print_exc()
        time.sleep(300)
if __name__ == '__main__':
    main()
