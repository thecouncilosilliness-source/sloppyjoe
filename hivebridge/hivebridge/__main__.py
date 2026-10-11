import argparse
import json
from pathlib import Path
from .core import Hive, Store, load_config
from .server import serve

DEFAULT_CONFIG = str(Path(__file__).resolve().parent.parent / 'council.demo.json')

def main():
    parser = argparse.ArgumentParser(description='HiveBridge v0.1 — Trinity/Council integration bridge')
    parser.add_argument('command', choices=['demo', 'serve'])
    parser.add_argument('--config', default=DEFAULT_CONFIG)
    parser.add_argument('--db', default='hive.db')
    parser.add_argument('--mode', choices=['trinity', 'council'], default='trinity')
    parser.add_argument('--text', default='Council, report readiness and next integration steps.')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if args.command == 'serve':
        serve(args.config, args.db, args.host, args.port)
    else:
        hive = Hive(load_config(args.config), Store(args.db))
        print(json.dumps(hive.run(args.text, args.mode), indent=2))

if __name__ == '__main__':
    main()
