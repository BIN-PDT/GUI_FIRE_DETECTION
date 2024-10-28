from os import environ
from roboflow import Roboflow
from dotenv import load_dotenv


load_dotenv()
API_KEY = environ.get("API_KEY")
WORKSPACE = environ.get("WORKSPACE")
PROJECT = environ.get("PROJECT")
VERSION = environ.get("VERSION")


if __name__ == "__main__":
    rf = Roboflow(api_key=API_KEY)
    project = rf.workspace(WORKSPACE).project(PROJECT)
    version = project.version(VERSION)
    version.deploy("yolov10", "model", "model.pt")
