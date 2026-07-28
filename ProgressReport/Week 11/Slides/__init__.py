import os
import importlib

def load_slides():
    slides = []
    current_dir = os.path.dirname(os.path.abspath(__file__))
    files = sorted(os.listdir(current_dir))
    for filename in files:
        if not filename.startswith("slide_"):
            continue
        if not filename.endswith(".py"):
            continue
        module_name = f"Slides.{filename[:-3]}"
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, "get_slide_data"):
                slide_data = module.get_slide_data()
                slide_data["filename"] = filename[:-3]
                slides.append(slide_data)
        except Exception as e:
            print(f"[-] Warning: Failed to import slide module {module_name}: {e}")
    return slides
