# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['movieProcess.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports = [
        'flet'
    ],

    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'pandas',
        # =========================
        # ML / DL / AI
        # =========================
        'torch','torchvision','torchaudio',
        'tensorflow','tensorflow_intel','keras','jax',
        'xgboost','lightgbm','catboost',
        'sklearn','scipy','statsmodels',
        'transformers','sentence_transformers',
        'sentencepiece','tokenizers',
        'whisper','openai_whisper','speechbrain',
        'stable_baselines3','gym','gymnasium',
        'optuna','ray','mlflow','mlflow_skinny',
        'shap','yellowbrick','pycaret',


        # =========================
        # scientific / numeric extras
        # =========================
        'numba','llvmlite','sympy','pmdarima','tbats',
        'pyamg','h5py','pyarrow',

        # =========================
        # plotting / viz
        # =========================
        'matplotlib','matplotlib_inline','seaborn',
        'plotly','bokeh','holoviews','panel','hvplot',
        'altair','kaleido','wordcloud',

        # =========================
        # CV / image / media
        # =========================
        'cv2','opencv_python','opencv_python_headless',
        'PIL','pillow','imageio','imageio_ffmpeg',
        'PyWavelets','pytesseract','pyzbar',

        # =========================
        # audio / video
        # =========================
        'librosa','soundfile','soxr','pyaudio',
        'ffmpeg','ffmpeg_python','audioread',
        'spleeter','noisereduce',

        # =========================
        # web / API / async
        # =========================
        'fastapi','flask','dash','uvicorn',
        'starlette','aiohttp','httpx','httptools',
        'websockets','trio','trio_websocket',
        'requests_oauthlib','oauthlib',

        # =========================
        # browser / automation / UI
        # =========================
        'playwright','selenium','webdriver_manager',
        'pywebview','easygui',

        # =========================
        # cloud / azure / google / aws
        # =========================
        'azure','boto3','botocore',
        'msal','msal_extensions',

        # =========================
        # jupyter / dev tools
        # =========================
        'ipykernel','ipython','notebook','jupyter',
        'jupyter_client','jupyter_core','ipywidgets',
        'pytest','pytest_cov','black','mypy',

        # =========================
        # database extras
        # =========================
        'sqlalchemy','alembic','psycopg2','pymysql',
        'pyodbc',

        # =========================
        # crypto / network
        # =========================
        'cryptography','pyopenssl','paramiko','bcrypt',
        'grpc','grpcio',

        # =========================
        # GIS / geo
        # =========================
        'rasterio','fiona','shapely','pyproj',
        'geopandas','folium','contextily',

        # =========================
        # misc huge ecosystems
        # =========================
        'spacy','nltk','gensim','stanza',
        'huggingface_hub','datasets',

        # =========================
        # tests / docs
        # =========================
        'test','tests','doctest',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='movieProcess',
    debug=False,
    upx=True,
    console=True,
)
