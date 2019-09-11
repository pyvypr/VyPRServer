"""
Main module for a test Flask-based web application.
"""

import sys
sys.path.append("VyPR")

from app import app_object

if __name__ == "__main__":

	# run the application
	app_object.run(host="0.0.0.0", debug=True, port=9001)
