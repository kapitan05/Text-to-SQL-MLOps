import os
import sys

root_dir = os.path.dirname(__file__)

sys.path.insert(0, os.path.abspath(os.path.join(root_dir, "app")))
sys.path.insert(0, os.path.abspath(os.path.join(root_dir, "ml")))
