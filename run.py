from app import app, backend
from argparse import ArgumentParser
import os

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--data', default=os.path.join("data", "OOgle"))
    args = parser.parse_args()
    backend.initialize(args.data)
    app.json_encoder = backend.MyEncoder
    app.run(host='0.0.0.0', debug=True)