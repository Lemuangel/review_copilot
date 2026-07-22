import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")

DATA_FILE = os.path.join(DATA_DIR, "Computers.json")
SAMPLE_SIZE = 10000
EMBEDDING_MODEL = os.path.join(BASE_DIR, "..", "bge-m3")
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50