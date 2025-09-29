import importlib

def test_import_insight_agent():
    importlib.import_module('insight_agent')


def test_import_streamlit_pages():
    # import top-level Streamlit pages to validate imports
    import os
    pages_dir = os.path.join('app','pages')
    for fn in os.listdir(pages_dir):
        if fn.endswith('.py'):
            module = f"app.pages.{fn[:-3]}"
            importlib.import_module(module)
