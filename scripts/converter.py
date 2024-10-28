from ultralytics import YOLO


if __name__ == "__main__":
    model = YOLO("model/model.pt")
    model.export(format="edgetpu")
