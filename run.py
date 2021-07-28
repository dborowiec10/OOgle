import sys
from app import app, backend
from argparse import ArgumentParser

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--data', default="data")
    args = parser.parse_args()
    backend.initialize(args.data)
    app.json_encoder = backend.MyEncoder
    app.run(debug=True)