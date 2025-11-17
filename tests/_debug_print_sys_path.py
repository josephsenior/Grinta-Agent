import sys

def pytest_sessionstart(session):
    print('\n=== DEBUG: sys.path at pytest session start ===')
    for p in sys.path:
        print(p)
    print('=== END sys.path ===\n')
