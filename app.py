from website import create_app


app = create_app()

application = app
 

if __name__ == '__main__':
    application.run(debug=True, use_reloader=False)