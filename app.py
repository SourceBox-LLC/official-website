from website import create_app
import os
# bug report google form link https://forms.gle/sA1Z1FRESpwFo6CJA

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=port)