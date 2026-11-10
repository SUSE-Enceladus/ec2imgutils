# Make sure the tests always exercise the source tree and not an
# ec2imgutils version that is installed on the system.
import os
import sys

lib_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'lib')
)
sys.path.insert(0, lib_path)
