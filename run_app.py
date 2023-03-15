from dash import Dash
import tempfile
import os
from pathlib import Path

app = Dash()

if __name__ == '__main__':
    from dashboard import main_page
    # cache_dir = tempfile.TemporaryDirectory()
    # print(f'Caching in {cache_dir.name}')
    project_dir = Path(__file__).parent
    cache_dir = project_dir / 'cache'
    app.layout = main_page.get_layout(app, str(cache_dir))
    try:
        app.run_server()
    except KeyboardInterrupt as e:
        pass
    # print('Cleaning up cache directory')
    # cache_dir.cleanup()
    # assert not os.path.exists(cache_dir.name), f'Failed to cleanup cache directory. Check {cache_dir.name}'
    # print('Successfully cleaned cache directory')
