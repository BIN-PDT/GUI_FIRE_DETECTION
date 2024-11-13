from io import BytesIO
from threading import Thread
from datetime import datetime
from utils import Timer, FirebaseUtil

import cv2
from ultralytics import YOLO
from cv2 import FONT_HERSHEY_SIMPLEX as CLS_FONT


MODEL_PATH = "resources/___.pt"


class App:
    def __init__(self):
        self.firebase = FirebaseUtil()
        self.model = YOLO(MODEL_PATH)
        self.camera = cv2.VideoCapture(0)
        # CONTROL.
        self.state = self.firebase.get_value("detect")
        self.detect_timer, self.upload_timer = Timer(10), Timer(2)
        self.is_detecting, self.timestamp, self.upload_quantity = False, None, 1

    def detect_image(self, image):
        result = self.model.predict(source=image, conf=0.5, verbose=False)[0]
        boxes = result.boxes.xyxy
        state = False

        if len(boxes) > 0:
            clses = result.boxes.cls
            cls_names = result.names

            for box, cls in zip(boxes, clses):
                cls_name = cls_names[int(cls)]

                if cls_name != "other":
                    state = True
                    t, l, r, b = map(int, box.tolist())
                    color = (40, 40, 190) if cls_name == "fire" else (210, 210, 210)
                    # DRAW BOUNDING BOX.
                    cv2.rectangle(image, (t, l), (r, b), color, 2)
                    # DRAW CLASS NAME.
                    cv2.putText(image, cls_name, (t, l - 10), CLS_FONT, 0.65, color)

        return state

    def handle_signal(self, state):
        if state or self.state != state:
            self.detect_timer.activate()
            self.state = state
            self.firebase.set_value(state, "detect")

            if state:
                self.is_detecting = True
                self.timestamp = datetime.now().strftime(r"%Y-%m-%d/%H:%M:%S")

                Thread(target=self.firebase.send_message).start()

    def handle_upload(self, image):
        if self.upload_quantity <= 3:
            if not self.upload_timer.is_active:
                _, image_encoded = cv2.imencode(".jpg", image)
                image_bytes = BytesIO(image_encoded.tobytes())
                args = image_bytes, self.timestamp, self.upload_quantity

                Thread(target=self.firebase.upload_image, args=args).start()
                self.upload_timer.activate()
                self.upload_quantity += 1
        else:
            self.is_detecting = False
            self.upload_timer.deactivate()
            self.timestamp, self.upload_quantity = None, 1

    def run(self):
        try:
            self.firebase.set_value(True, "online")
            while True:
                # UPDATE TIMER.
                self.detect_timer.update()
                self.upload_timer.update()
                # GET FRAME.
                ret, frame = self.camera.read()
                if not ret:
                    break
                # DETECT FRAME.
                state = self.detect_image(frame)
                cv2.imshow("Detection Application", frame)
                # CHECK SEND MESSAGE.
                if not self.detect_timer.is_active:
                    self.handle_signal(state)
                # CHECK UPLOAD IMAGE.
                if self.is_detecting:
                    self.handle_upload(frame)
                # CHECK QUIT.
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            self.firebase.set_value(False, "online")
            # RELEASE RESOURCE.
            self.camera.release()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    App().run()
