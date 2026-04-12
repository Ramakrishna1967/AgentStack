import sys
import pytest

with open('pytest_out.txt', 'w', encoding='utf-8') as f:
    sys.stdout = f
    sys.stderr = f
    pytest.main(['--collect-only', '--tb=short', '--disable-warnings'])
