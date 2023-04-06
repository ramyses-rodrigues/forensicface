# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_forensicface.ipynb.

# %% auto 0
__all__ = ['ForensicFace']

# %% ../nbs/00_forensicface.ipynb 2
from nbdev.showdoc import *
from fastcore.utils import *
import onnxruntime
import cv2
import numpy as np
import os.path as osp
from glob import glob
from insightface.app import FaceAnalysis
from insightface.utils import face_align


# %% ../nbs/00_forensicface.ipynb 3
class ForensicFace:
    """
    Class for processing facial images to extract useful features for forensic analysis.
    """

    def __init__(
        self,
        model: str = "sepaelv2",
        det_size: int = 320,
        use_gpu: bool = True,
        gpu: int = 0,  # which GPU to use
        magface=False,
        extended=True,
    ):
        """
        A face comparison tool for forensic analysis and comparison of facial images.

        Args:
        - model (str): The name of the face recognition model to use (default: "sepaelv2").
        - det_size (int): The size of the input images for face detection (default: 320).
        - use_gpu (bool): Whether to use a GPU for inference (default: True).
        - gpu (int): The ID of the GPU to use (default: 0).
        - magface (bool): Whether to use MagFace for face recognition (default: False).
        - extended (bool): Whether to use extended modules (detection, landmark_3d_68, genderage) (default: True).
        """
        self.extended = extended
        if self.extended == True:
            allowed_modules = ["detection", "landmark_3d_68", "genderage"]
        else:
            allowed_modules = ["detection"]

        self.det_size = (det_size, det_size)

        self.magface = magface

        self.model = model

        self.detectmodel = FaceAnalysis(
            name=model,
            allowed_modules=allowed_modules,
            providers=[("CUDAExecutionProvider", {"device_id": gpu})]
            if use_gpu
            else ["CPUExecutionProvider"],
        )
        self.detectmodel.prepare(ctx_id=gpu if use_gpu else -1, det_size=self.det_size)

        onnx_rec_model = glob(
            osp.join(
                osp.expanduser("~/.insightface/models"),
                model,
                "adaface",
                "adaface_*.onnx",
            )
        )
        assert len(onnx_rec_model) == 1
        self.ort_ada = onnxruntime.InferenceSession(
            onnx_rec_model[0],
            providers=[("CUDAExecutionProvider", {"device_id": gpu})]
            if use_gpu
            else ["CPUExecutionProvider"],
        )

        if self.magface:
            self.ort_mag = onnxruntime.InferenceSession(
                osp.join(
                    osp.expanduser("~/.insightface/models"),
                    model,
                    "magface",
                    "magface_iresnet100.onnx",
                ),
                providers=[("CUDAExecutionProvider", {"device_id": gpu})]
                if use_gpu
                else ["CPUExecutionProvider"],
            )

        if model == "sepaelv2":
            self.ort_fiqa = onnxruntime.InferenceSession(
                osp.join(
                    osp.expanduser("~/.insightface/models"),
                    model,
                    "cr_fiqa",
                    "cr_fiqa_l.onnx",
                ),
                providers=[("CUDAExecutionProvider", {"device_id": gpu})]
                if use_gpu
                else ["CPUExecutionProvider"],
            )

    def _to_input_ada(self, aligned_bgr_img):
        """
        Preprocesses the input face for the face recognition model.

        Args:
            face: Face image as a numpy array in BGR order.

        Returns:
            Preprocessed face image as a numpy array.
        """
        _aligned_bgr_img = aligned_bgr_img.astype(np.float32)
        _aligned_bgr_img = ((_aligned_bgr_img / 255.0) - 0.5) / 0.5
        return _aligned_bgr_img.transpose(2, 0, 1).reshape(1, 3, 112, 112)

    def _to_input_mag(self, aligned_bgr_img):
        """
        Preprocesses the input face for the MagFace model.

        Args:
            face: Face image as a numpy array in BGR order.

        Returns:
            Preprocessed face image as a numpy array.
        """
        _aligned_bgr_img = aligned_bgr_img.astype(np.float32)
        _aligned_bgr_img = _aligned_bgr_img / 255.0
        return _aligned_bgr_img.transpose(2, 0, 1).reshape(1, 3, 112, 112)

    def get_most_central_face(self, img, faces):
        """
        Get the keypoints of the most central face in an image.

        Args:
            img: Input image as a numpy array.
            faces: An insightface object with keypoints and bounding_box.

        Returns:
            Tuple containing the index of the most central face and its keypoints.
        """
        assert faces is not None
        img_center = np.array([img.shape[0] // 2, img.shape[1] // 2])
        dist = []

        # Compute centers of faces and distances from certer of image
        for idx, face in enumerate(faces):
            box = face.bbox.astype("int").flatten()
            face_center = np.array([(box[0] + box[2]) // 2, (box[1] + box[3]) // 2])
            dist.append(np.linalg.norm(img_center - face_center))

        # Get index of the face closest to the center of image
        idx = dist.index(min(dist))
        return idx, faces[idx].kps

    def get_larger_face(self, img, faces):
        """
        Get the keypoints of the larger face in an image.

        Args:
            img: Input image as a numpy array.
            faces: An insightface object with keypoints and bounding_box.

        Returns:
            Tuple containing the index of the larger face and its keypoints.
        """
        assert faces is not None
        areas = []

        # Compute centers of faces and distances from certer of image
        for idx, face in enumerate(faces):
            box = face.bbox.astype("int").flatten()
            areas.append(abs((box[2] - box[0]) * (box[3] - box[1])))

        # Get index of the face closest to the center of image
        idx = areas.index(max(areas))
        return idx, faces[idx].kps

    def process_image_single_face(self, imgpath: str):  # Path to image to be processed
        """
        Process a an image considering it has a single face and extract useful features for forensic analysis.

        Args:
            imgpath: Path to the input image.

        Returns:
            A dictionary containing the following keys:
                - 'keypoints': A 2D numpy array of shape (5, 2) containing the facial keypoints
                        for each face in the image. The keypoints are ordered as follows:
                       left eye, right eye, nose tip, left mouth corner, and right mouth corner.

                - 'ipd': A float representing the inter-pupillary distance for each face in the image.

                - 'embedding': A 1D numpy array of shape (512,) containing the facial embedding
                       for each face in the image.

                - 'norm': A float representing the L2 norm of the embedding for each face in the image.

                - 'bbox': A 1D numpy array of shape (4,) containing the bounding box coordinates for each face
                  in the image. The coordinates are ordered as follows: (xmin, ymin, xmax, ymax).

                - 'aligned_face': A 3D numpy array of shape (H, W, C) in RGB order containing the aligned face image for
                          each face in the image. The image has been cropped and aligned based on the
                          facial keypoints.

                If the 'extended' attribute is set to True, the dictionary will also contain the following keys:
                - 'gender': A string representing the gender for each face in the image.
                               Possible values are 'M' for male and 'F' for female.

                - 'age': An integer representing the estimated age for each face in the image.

                - 'pitch': A float representing the pitch angle for each face in the image.

                - 'yaw': A float representing the yaw angle for each face in the image.

                - 'roll': A float representing the roll angle for each face in the image.

                If the 'magface' attribute is set to True, the dictionary will also contain the following keys:
                - 'magface_embedding': A 1D numpy array of shape (512,) containing the magface
                                          embedding for each face in the image.

                - 'magface_norm': A float representing the L2 norm of the magface embedding for
                                     each face in the image.
        """
        if type(imgpath) == str:  # image path passed as argument
            bgr_img = cv2.imread(imgpath)
        else:  # image array passed as argument
            bgr_img = imgpath.copy()
        faces = self.detectmodel.get(bgr_img)
        if len(faces) == 0:
            return {}

        idx, kps = self.get_larger_face(bgr_img, faces)

        bbox = faces[idx].bbox.astype("int")
        bgr_aligned_face = face_align.norm_crop(bgr_img, kps)
        ipd = np.linalg.norm(kps[0] - kps[1])

        ada_inputs = {
            self.ort_ada.get_inputs()[0].name: self._to_input_ada(bgr_aligned_face)
        }
        normalized_embedding, norm = self.ort_ada.run(None, ada_inputs)

        ret = {
            "keypoints": kps,
            "ipd": ipd,
            "embedding": normalized_embedding.flatten() * norm.flatten()[0],
            "norm": norm.flatten()[0],
            "bbox": bbox,
            "aligned_face": cv2.cvtColor(bgr_aligned_face, cv2.COLOR_BGR2RGB),
        }

        if self.extended:
            gender = "M" if faces[idx].gender == 1 else "F"
            age = faces[idx].age
            pitch, yaw, roll = faces[idx].pose
            ret = {
                **ret,
                **{
                    "gender": gender,
                    "age": age,
                    "pitch": pitch,
                    "yaw": yaw,
                    "roll": roll,
                },
            }

        if self.magface:
            # mag_inputs = {self.ort_mag.get_inputs()[0].name: self._to_input_mag(bgr_aligned_face)}
            mag_embedding = self.ort_mag.run(None, ada_inputs)[0][0]
            mag_norm = np.linalg.norm(mag_embedding)
            ret = {
                **ret,
                **{
                    "magface_embedding": mag_embedding,
                    "magface_norm": mag_norm,
                },
            }

        if self.model == "sepaelv2":
            _, fiqa_score = self.ort_fiqa.run(None, ada_inputs)
            ret = {**ret, "fiqa_score": fiqa_score[0][0]}

        return ret

    def process_image(self, imgpath):
        return self.process_image_single_face(imgpath)

    def process_image_multiple_faces(
        self,
        imgpath: str,  # Path to image to be processed
    ):
        """
        Process an image with one or multiple faces and returns a list of dictionaries
        with the following keys:

            - 'keypoints': A 2D numpy array of shape (5, 2) containing the facial keypoints
                            for each face in the image. The keypoints are ordered as follows:
                            left eye, right eye, nose tip, left mouth corner, and right mouth corner.

            - 'ipd': A float representing the inter-pupillary distance for each face in the image.

            - 'embedding': A 1D numpy array of shape (512,) containing the facial embedding
                            for each face in the image.

            - 'norm': A float representing the L2 norm of the embedding for each face in the image.

            - 'bbox': A 1D numpy array of shape (4,) containing the bounding box coordinates for each face
                        in the image. The coordinates are ordered as follows: (xmin, ymin, xmax, ymax).

            - 'aligned_face': A numpy array of shape (112, 112, 3) in RGB order containing the aligned face image for
                                each face in the image. The image has been cropped and aligned based on the
                                facial keypoints.

         If the 'extended' attribute is set to True, the dictionaries will also contain the following keys:
            - 'gender': A string representing the sex for each face in the image.
                        Possible values are 'M' for male and 'F' for female.

            - 'age': An integer representing the estimated age for each face in the image.

            - 'pitch': A float representing the pitch angle for each face in the image.

            - 'yaw': A float representing the yaw angle for each face in the image.

            - 'roll: A float representing the roll angle for each face in the image.

         If the 'magface' attribute is set to True, the dictionary will also contain the following keys:
            - 'magface_embedding': A 1D numpy array of shape (512,) containing the magface
                                    embedding for each face in the image.

            - 'magface_norm': A float representing the L2 norm of the magface embedding for
                                each face in the image.

        Args:
            - imgpath (str): The file path to the image to be processed.

        Returns:
            - A list of dictionaries, with each dictionary representing a face in the image.
        """
        if type(imgpath) == str:  # image path passed as argument
            bgr_img = cv2.imread(imgpath)
        else:  # image array passed as argument
            bgr_img = imgpath.copy()
        faces = self.detectmodel.get(bgr_img)
        if len(faces) == 0:
            return []
        ret = []
        for face in faces:
            kps = face.kps
            bbox = face.bbox.astype("int")
            bgr_aligned_face = face_align.norm_crop(bgr_img, kps)
            ipd = np.linalg.norm(kps[0] - kps[1])
            ada_inputs = {
                self.ort_ada.get_inputs()[0].name: self._to_input_ada(bgr_aligned_face)
            }
            normalized_embedding, norm = self.ort_ada.run(None, ada_inputs)
            face_ret = {
                "keypoints": kps,
                "ipd": ipd,
                "embedding": normalized_embedding.flatten() * norm.flatten()[0],
                "norm": norm.flatten()[0],
                "bbox": bbox,
                "aligned_face": cv2.cvtColor(bgr_aligned_face, cv2.COLOR_BGR2RGB),
            }

            if self.extended:
                gender = "M" if face.gender == 1 else "F"
                age = face.age
                pitch, yaw, roll = face.pose
                face_ret = {
                    **face_ret,
                    **{
                        "gender": gender,
                        "age": age,
                        "pitch": pitch,
                        "yaw": yaw,
                        "roll": roll,
                    },
                }

            if self.magface:
                # mag_inputs = {self.ort_mag.get_inputs()[0].name: self._to_input_mag(bgr_aligned_face)}
                mag_embedding = self.ort_mag.run(None, ada_inputs)[0][0]
                mag_norm = np.linalg.norm(mag_embedding)
                face_ret = {
                    **face_ret,
                    **{"magface_embedding": mag_embedding, "magface_norm": mag_norm},
                }

            if self.model == "sepaelv2":
                _, fiqa_score = self.ort_fiqa.run(None, ada_inputs)
                face_ret = {**face_ret, "fiqa_score": fiqa_score[0][0]}
                

            ret.append(face_ret)
        return ret


# %% ../nbs/00_forensicface.ipynb 9
@patch
def compare(self: ForensicFace, img1path: str, img2path: str):
    """
    Compares the similarity between two face images based on their embeddings.

    Parameters:
        - img1path (str): Path to the first image file
        - img2path (str): Path to the second image file

    Returns:
        A float representing the similarity score between the two faces based on their embeddings.
        The score ranges from -1.0 to 1.0, where 1.0 represents a perfect match and -1.0 represents a complete mismatch.
    """
    img1data = self.process_image(img1path)
    assert len(img1data) > 0, f"No face detected in {img1path}"
    img2data = self.process_image(img2path)
    assert len(img2data) > 0, f"No face detected in {img2path}"
    return np.dot(img1data["embedding"], img2data["embedding"]) / (
        img1data["norm"] * img2data["norm"]
    )


# %% ../nbs/00_forensicface.ipynb 12
@patch
def aggregate_embeddings(self: ForensicFace, embeddings, weights=None):
    """
    Aggregates multiple embeddings into a single embedding.

    Args:
        embeddings (numpy.ndarray): A 2D array of shape (num_embeddings, embedding_dim) containing the embeddings to be
            aggregated.
        weights (numpy.ndarray, optional): A 1D array of shape (num_embeddings,) containing the weights to be assigned
            to each embedding. If not provided, all embeddings are equally weighted.

    Returns:
        numpy.ndarray: A 1D array of shape (embedding_dim,) containing the aggregated embedding.
    """
    if weights is None:
        weights = np.ones(embeddings.shape[0], dtype="int")
    assert embeddings.shape[0] == weights.shape[0]
    return np.average(embeddings, axis=0, weights=weights)


# %% ../nbs/00_forensicface.ipynb 13
@patch
def aggregate_from_images(self: ForensicFace, list_of_image_paths):
    """
    Given a list of image paths, this method returns the average embedding of all faces found in the images.

    Args:
        list_of_image_paths (List[str]): List of paths to images.

    Returns:
        Union[np.ndarray, List]: If one or more faces are found, returns a 1D numpy array of shape (512,) representing the
        average embedding. Otherwise, returns an empty list.
    """
    embeddings = []
    weights = []
    for imgpath in list_of_image_paths:
        d = self.process_image(imgpath)
        if len(d) > 0:
            embeddings.append(d["embedding"])
    if len(embeddings) > 0:
        return self.aggregate_embeddings(np.array(embeddings))
    else:
        return []


# %% ../nbs/00_forensicface.ipynb 18
@patch
def _get_extended_bbox(self: ForensicFace, bbox, frame_shape, margin_factor):
    """
    Computes and returns the bounding box with extended margins.

    Parameters:
        bbox (ndarray): The bounding box coordinates (startX, startY, endX, endY).
        frame_shape (tuple): The shape of the video frame (height, width, channels).
        margin_factor (float): The factor to be applied for computing the margin.

    Returns:
        A list with the coordinates of the extended bounding box (startX_out, startY_out, endX_out, endY_out).
    """
    # add a margin on the bounding box
    (startX, startY, endX, endY) = bbox.astype("int")
    (h, w) = frame_shape[:2]
    out_width = (endX - startX) * margin_factor
    out_height = (endY - startY) * margin_factor

    startX_out = int((startX + endX) / 2 - out_width / 2)
    endX_out = int((startX + endX) / 2 + out_width / 2)
    startY_out = int((startY + endY) / 2 - out_height / 2)
    endY_out = int((startY + endY) / 2 + out_height / 2)

    # tests if the output bbox coordinates are out of frame limits
    if startX_out < 0:
        startX_out = 0
    if endX_out > int(w):
        endX_out = int(w)
    if startY_out < 0:
        startY_out = 0
    if endY_out > int(h):
        endY_out = int(h)
    return [startX_out, startY_out, endX_out, endY_out]


@patch
def extract_faces(
    self: ForensicFace,
    video_path: str,  # path to video file
    dest_folder: str = None,  # folder used to save extracted faces. If not provided, a new folder with the video name is created
    every_n_frames: int = 1,  # skip some frames
    margin: float = 2.0,  # margin to add to each face, w.r.t. detected bounding box
    start_from: float = 0.0,  # seconds after video start to begin processing
):
    """
    Extracts faces from a video and saves them as individual images.

    Parameters:
        video_path (str): The path to the input video file.
        dest_folder (str, optional): The path to the output folder. If not provided, a new folder with the same name as the input video file is created.
        every_n_frames (int, optional): Extract faces from every n-th frame. Default is 1 (extract faces from all frames).
        margin (float, optional): The factor by which the detected face bounding box should be extended. Default is 2.0.
        start_from (float, optional): The time point (in seconds) after which the video frames should be processed. Default is 0.0.

    Returns:
        The number of extracted faces.
    """
    if dest_folder is None:
        dest_folder = os.path.splitext(video_path)[0]

    os.makedirs(dest_folder, exist_ok=True)

    # initialize video stream from file
    vs = cv2.VideoCapture(video_path)
    fps = vs.get(cv2.CAP_PROP_FPS)
    start_frame = int(fps * start_from)

    # seek to starting frame
    vs.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    current_frame = start_frame
    nfaces = 0
    while True:

        if (current_frame % every_n_frames) != 0:
            current_frame = current_frame + 1
            continue
        
        vs.set(cv2.CAP_PROP_POS_FRAMES, current_frame) 
        ret, frame = vs.read()

        if not ret:
            break
        current_frame = current_frame + 1
        (h, w) = frame.shape[:2]

        faces = self.detectmodel.get(frame)
        for i, face in enumerate(faces):
            startX, startY, endX, endY = face.bbox.astype("int")
            faceW = endX - startX
            faceH = endY - startY
            outBbox = self._get_extended_bbox(
                face.bbox, frame.shape, margin_factor=margin
            )
            # export the face (with added margin)
            face_crop = frame[outBbox[1] : outBbox[3], outBbox[0] : outBbox[2]]
            face_img_path = os.path.join(
                dest_folder, f"frame_{current_frame:07}_face_{i:02}.png"
            )
            cv2.imwrite(face_img_path, face_crop)
            nfaces += 1
    vs.release()
    return nfaces

