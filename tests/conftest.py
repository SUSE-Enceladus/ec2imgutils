import os
import sys

# Always test the code in the source tree, never an installed copy of
# ec2imgutils that may be present in site-packages.
code_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'lib')
)
if code_path in sys.path:
    sys.path.remove(code_path)
sys.path.insert(0, code_path)
