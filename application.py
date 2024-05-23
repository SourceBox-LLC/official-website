from website import create_app


application = create_app()



 

if __name__ == '__main__':
    application.run(debug=True, use_reloader=False, host="0.0.0.0", port=80)