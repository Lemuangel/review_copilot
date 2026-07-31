import requests

url = "http://127.0.0.1:8000/reviews/upload"
file_path = "data/output/full_dataset.csv"

with open(file_path, "rb") as f:
    files = {"file": (file_path, f, "text/csv")}
    response = requests.post(url, files=files)

print(response.status_code)
print(response.json())