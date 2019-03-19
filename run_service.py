"""
Main module for a test Flask-based web application.
"""

from app import app_object

if __name__ == "__main__":

	# run the application
	app_object.run(host="0.0.0.0", debug=True, port=9001)
