"""Test NVIDIA NIM with synthetic text using the app's model fallback."""
import argparse
import getpass
import os

from ai_service import AIError, NvidiaProvider, WritingRequest
from local_config import load_local_env


def main():
    load_local_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', help='Preferred NVIDIA model to try before the backups.')
    args = parser.parse_args()
    key = os.getenv('NVIDIA_API_KEY', '').strip()
    if not key:
        key = getpass.getpass('NVIDIA API key (input is hidden): ').strip()
    if not key:
        print('No key entered. Test cancelled.')
        return 1
    provider = NvidiaProvider(api_key=key, model=args.model)
    print(f'Testing NVIDIA models: {", ".join(provider.models)}')
    try:
        provider.suggest(WritingRequest('Built Python tools.', 'projects'))
    except AIError as error:
        print(error)
        return 1
    print(f'Success: {provider.last_model} returned a valid suggestion.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
