import os
venv_path = os.path.dirname(os.path.dirname(os.__file__))
print(os.path.join(venv_path, 'Scripts'))  # 应输出类似 C:\path\to\venv\Scripts