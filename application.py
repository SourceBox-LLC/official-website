from website import create_app
import os


application = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    application.run(debug=True, use_reloader=False, host="0.0.0.0", port=port) #was port 80