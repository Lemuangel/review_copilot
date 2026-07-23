import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
SAMPLE_SIZE = None
EMBEDDING_MODEL = os.path.abspath(os.path.join(BASE_DIR, "..", "bge-m3"))
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50