from time import time
from firebase_admin import initialize_app, credentials, db, messaging, storage


FIREBASE_API_KEY_PATH = "resources/___.json"


class Timer:
    def __init__(self, duration):
        self.duration = duration
        self.is_active = False
        self.start_time = None

    def activate(self):
        self.is_active = True
        self.start_time = time()

    def deactivate(self):
        self.is_active = False
        self.start_time = None

    def update(self):
        if self.is_active and time() - self.start_time >= self.duration:
            self.deactivate()


class FirebaseUtil:
    DEVICE_ID = "CAM_001"
    DEVICE_NAME = "CAMERA DEVICE"
    INFO_TITLE = "NOTIFICATION OF {}"
    INFO_BODY = "HAZARD DETECTED"

    def __init__(self):
        self.on_ready()
        self.on_event()

    def on_ready(self):
        # FOR USING FIREBASE SERVICES.
        SERVICE_ACCOUNT_KEY_PATH = FIREBASE_API_KEY_PATH
        # FOR USING REALTIME DATABASE SERVICE.
        DATABASE_URL = "https://fire-detection-3819f-default-rtdb.asia-southeast1.firebasedatabase.app/"
        # FOR USING STORAGE SERVICE.
        STORAGE_BUCKET_URL = "fire-detection-3819f.appspot.com"

        try:
            cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
            initialize_app(
                cred,
                {
                    "databaseURL": DATABASE_URL,
                    "storageBucket": STORAGE_BUCKET_URL,
                },
            )
        except:
            raise Exception("Can not connect to Firebase.")

    def on_event(self):
        # DEFAULT SETTINGS.
        if not self.get_value():
            self.set_value(self.DEVICE_NAME, "name")
            self.set_value(False, "detect")
            self.set_value(False, "online")
        # CONFIGURED SETTINGS.
        else:
            self.DEVICE_NAME = self.get_value("name")
        self.INFO_TITLE = self.INFO_TITLE.format(self.DEVICE_NAME)
        # GENERAL SETTINGS.
        self.bucket = storage.bucket()
        self.token = self.get_token()

    def get_token(self):
        try:
            ref = db.reference(f"devices/{self.DEVICE_ID}/users")
            users = ref.get()
            for user_id, is_owner in users.items():
                if is_owner:
                    ref = db.reference(f"users/{user_id}/token")
                    token = ref.get()
                    return token
        except ValueError:
            raise Exception("Wrong syntax.")
        except db.exceptions.FirebaseError:
            raise Exception("Can not connect to Realtime Database.")

    def send_message(self):
        if self.token:
            message = messaging.Message(
                token=self.token,
                data={
                    "title": self.INFO_TITLE,
                    "body": self.INFO_BODY,
                    "device_id": self.DEVICE_ID,
                    "device_name": self.DEVICE_NAME,
                },
            )
            try:
                messaging.send(message)
            except ValueError:
                raise Exception("Invalid message.")
            except messaging.exceptions.FirebaseError:
                raise Exception("Can not send message.")

    def upload_image(self, file_stream, timestamp, upload_index):
        unique_id = f"{timestamp}_{upload_index}"
        blob_name = f"captured/{self.DEVICE_ID}/{unique_id}"
        # UPLOAD TO STORAGE.
        blob = self.bucket.blob(blob_name)
        try:
            blob.upload_from_file(file_stream, content_type="image/jpeg")
        except:
            pass
        else:
            blob.make_public()
            # UPLOAD TO DATABASE.
            self.set_value(blob.public_url, "captured", timestamp, str(upload_index))

    @classmethod
    def get_value(cls, *components):
        try:
            ref = db.reference("/".join(("devices", cls.DEVICE_ID, *components)))
            return ref.get()
        except ValueError:
            raise Exception("Wrong syntax.")
        except db.exceptions.FirebaseError:
            raise Exception("Can not connect to Realtime Database.")

    @classmethod
    def set_value(cls, value, *components):
        try:
            ref = db.reference("/".join(("devices", cls.DEVICE_ID, *components)))
            ref.set(value)
        except (ValueError, TypeError):
            raise Exception("Invalid value.")
        except db.exceptions.FirebaseError:
            raise Exception("Can not connect to Realtime Database.")
