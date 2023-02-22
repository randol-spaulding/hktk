from dash import Dash

app = Dash()

if __name__ == '__main__':
    from dashboard import main_page
    app.layout = main_page.get_layout(app)
    app.run_server()
