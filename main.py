import cv2
import numpy as np
import customtkinter as ctk

from PIL import Image
from pygame import mixer
from ultralytics import YOLO
from cv2 import FONT_HERSHEY_SIMPLEX as CLS_FONT


# SETTINGS.
PATH_AUDIO = r"audio\warning.wav"
PATH_MODEL = r"model\model.pt"


class ControlFrame(ctk.CTkFrame):
    def __init__(self, parent, webc_control, conf_control, path_control):
        super().__init__(master=parent, fg_color="transparent")
        self.pack(padx=20, pady=20)
        # DATA.
        self.webc_control = webc_control
        self.conf_control = conf_control
        self.path_control = path_control
        self.webc_control.trace_add("write", self.update_device_switch)
        # WIDGET.
        self.device_switch = ctk.CTkSwitch(
            master=self,
            width=150,
            text="Image/Video",
            font=("Rockwell Condensed", 18),
            variable=webc_control,
        )
        self.device_switch.pack(side=ctk.LEFT, padx=10)

        self.upload_button = ctk.CTkButton(
            master=self,
            height=40,
            cursor="hand2",
            text="Upload File",
            font=("Cambria", 16, "bold", "italic"),
            command=self.upload_file,
        )
        self.upload_button.pack(side=ctk.LEFT)

        self.confidence_label = ctk.CTkLabel(
            master=self,
            width=125,
            text=f"Confidence ({self.conf_control.get():.0%})",
            font=("Rockwell Condensed", 18),
        )
        self.confidence_label.pack(side=ctk.LEFT, padx=10)

        ctk.CTkSlider(
            master=self, variable=conf_control, command=self.update_confidence_label
        ).pack(side=ctk.LEFT)

    def update_device_switch(self, *args):
        if self.webc_control.get():
            self.path_control.set("")
            self.upload_button.configure(state=ctk.DISABLED)
            self.device_switch.configure(text="Webcam")
        else:
            self.upload_button.configure(state=ctk.NORMAL)
            self.device_switch.configure(text="Image/Video")

    def update_confidence_label(self, *args):
        self.confidence_label.configure(
            text=f"Confidence ({self.conf_control.get():.0%})"
        )

    def upload_file(self):
        path = ctk.filedialog.askopenfilename(
            title="Select an image or a video file",
            filetypes=[("Image & Video", "*jpg *png *.mp4")],
        )
        if path:
            self.path_control.set(path)


class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color="black")
        ctk.set_appearance_mode("dark")
        # SETUP.
        self.geometry("980x680")
        self.resizable(False, False)
        self.title("")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        # DATA.
        self.on_load()
        self.webc_control = ctk.BooleanVar(value=False)
        self.conf_control = ctk.DoubleVar(value=0.5)
        self.path_control = ctk.StringVar()
        self.webc_control.trace_add("write", self.update_device)
        self.path_control.trace_add("write", self.update_device)
        # WIDGET.
        self.screen = ctk.CTkLabel(self, text="")
        self.screen.pack(expand=ctk.TRUE, fill=ctk.BOTH, padx=20, pady=20)
        ControlFrame(self, self.webc_control, self.conf_control, self.path_control)

    def on_load(self):
        # AUDIO.
        mixer.init(channels=1)
        self.channel = mixer.Channel(0)
        self.audio = mixer.Sound(PATH_AUDIO)
        self.audio.set_volume(0.25)
        # MODEL.
        self.model = YOLO(PATH_MODEL)
        # CAMERA.
        self.camera = None
        self.event_id = None

    def on_close(self):
        if self.camera:
            self.camera.release()
        self.destroy()

    def update_device(self, *args):
        # RELEASE RESOURCES.
        if self.camera:
            self.camera.release()
            self.off_screen(self.screen)
            self.after_cancel(self.event_id)
        # CHANGE DEVICE MODE.
        if self.webc_control.get():
            self.camera = cv2.VideoCapture(0)
            self.event_id = self.after(10, self.update_frame)
        else:
            if path := self.path_control.get():
                if path.endswith(("jpg", "png")):
                    image = cv2.imread(path)
                    self.display_image(image)
                else:
                    self.camera = cv2.VideoCapture(path)
                    self.event_id = self.after(10, self.update_frame)

    def display_image(self, image):
        # DETECT IMAGE.
        image = self.detect_image(image)
        # CONVERT TO PIL MODE.
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # CREATE PIL IMAGE.
        image = Image.fromarray(image)
        # CREATE CTK IMAGE.
        image = ctk.CTkImage(image, size=(900, 560))
        # CHANGE IMAGE DISPLAY.
        self.screen.configure(image=image)

    def update_frame(self):
        ret, frame = self.camera.read()
        if ret:
            self.display_image(frame)
        self.event_id = self.after(10, self.update_frame)

    def detect_image(self, image):
        result = self.model.predict(
            source=image, conf=self.conf_control.get(), verbose=False
        )[0]
        boxes = result.boxes.xyxy

        if len(boxes) > 0:
            is_detected = False
            clses = result.boxes.cls
            cls_names = result.names

            for box, cls in zip(boxes, clses):
                cls_name = cls_names[int(cls)]
                if cls_name != "other":
                    is_detected = True
                    t, l, r, b = map(int, box.tolist())
                    color = (40, 40, 190) if cls_name == "fire" else (210, 210, 210)
                    # DRAW BOUNDING BOX.
                    cv2.rectangle(image, (t, l), (r, b), color, 2)
                    # DRAW CLASS NAME.
                    cv2.putText(image, cls_name, (t, l - 10), CLS_FONT, 0.65, color)
            # PLAY WARNING SOUND.
            if is_detected and not self.channel.get_busy():
                self.channel = self.audio.play()
        return image

    @staticmethod
    def off_screen(screen):
        black_frame = np.zeros((560, 900, 3), dtype=np.uint8)
        black_image = Image.fromarray(black_frame)
        black_image_ctk = ctk.CTkImage(black_image, size=(900, 560))
        screen.configure(image=black_image_ctk)


if __name__ == "__main__":
    App().mainloop()
