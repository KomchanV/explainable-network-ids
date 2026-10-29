"""Export the API schema without starting the lifespan or loading Joblib."""
import argparse
import json
from pathlib import Path
from apps.api.main import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / 'packages/api-client/openapi.json'
    content = json.dumps(create_app().openapi(), indent=2, sort_keys=True) + '\n'
    if args.check:
        if not path.is_file() or path.read_text() != content:
            parser.exit(1, 'OpenAPI is stale. Run pnpm contract:generate.\n')
        print('OpenAPI matches FastAPI.')
    else:
        path.write_text(content)
        print(f'Exported {path.relative_to(path.parents[2])}')


if __name__ == '__main__':
    main()
